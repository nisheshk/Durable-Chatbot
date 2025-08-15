#!/usr/bin/env python3
"""
Enhanced scalability test for agent-based tool selection chatbot.

This script tests concurrent sessions with the AI-powered tool selection
system using parametrized session counts for comprehensive load testing.

Features:
- Tests configurable concurrent sessions (default: 50)
- Each session sends 5 sequential messages with response validation
- Real-time concurrent execution using asyncio
- Enhanced performance metrics and resource monitoring
- Command-line configuration support

Usage:
    python test_scalability_simple.py --sessions 50 --messages 5
    python test_scalability_simple.py --help
    
Environment Variables:
    SCALABILITY_SESSIONS=50    # Number of concurrent sessions
    SCALABILITY_MESSAGES=5     # Messages per session
"""

import asyncio
import time
import uuid
import statistics
import argparse
import os
from datetime import datetime
from pathlib import Path
import sys

# Add chatbot_backend to path
sys.path.insert(0, str(Path(__file__).parent))

from temporalio.client import Client
from workflows.chat_workflow import SignalQueryOpenAIWorkflow
from config_cloud import cloud_config


def parse_arguments():
    """Parse command-line arguments for test configuration."""
    parser = argparse.ArgumentParser(
        description="Enhanced scalability test for AI chatbot with tool selection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python test_scalability_simple.py                    # Default: 50 sessions, 5 messages
    python test_scalability_simple.py --sessions 20      # 20 sessions, 5 messages
    python test_scalability_simple.py --sessions 100 --messages 3  # 100 sessions, 3 messages
    python test_scalability_simple.py --timeout 60       # Custom timeout
        """
    )
    
    parser.add_argument(
        '--sessions', '-s',
        type=int,
        default=int(os.getenv('SCALABILITY_SESSIONS', 50)),
        help='Number of concurrent sessions to test (default: 50, max: 200)'
    )
    
    parser.add_argument(
        '--messages', '-m', 
        type=int,
        default=int(os.getenv('SCALABILITY_MESSAGES', 5)),
        help='Number of messages per session (default: 5, max: 10)'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=int(os.getenv('SCALABILITY_TIMEOUT', 60)),
        help='Timeout per message in seconds (default: 60)'
    )
    
    parser.add_argument(
        '--skip-confirmation',
        action='store_true',
        help='Skip worker confirmation prompt (useful for automation)'
    )
    
    args = parser.parse_args()
    
    # Validation
    if args.sessions < 1 or args.sessions > 200:
        parser.error(f"Sessions must be between 1 and 200 (got {args.sessions})")
    if args.messages < 1 or args.messages > 10:
        parser.error(f"Messages must be between 1 and 10 (got {args.messages})")
    if args.timeout < 10 or args.timeout > 300:
        parser.error(f"Timeout must be between 10 and 300 seconds (got {args.timeout})")
        
    return args


async def send_message_to_session(client, workflow_id, message, user_id=None, is_first_message=False, timeout=60):
    """Send a message to a session and wait for the AI response with enhanced validation."""
    start_time = time.time()
    
    try:
        if is_first_message:
            # Start new workflow
            workflow_handle = await client.start_workflow(
                SignalQueryOpenAIWorkflow.run,
                args=[cloud_config.INACTIVITY_TIMEOUT_MINUTES, user_id],
                id=workflow_id,
                task_queue=cloud_config.TASK_QUEUE,
                start_signal="user_prompt",
                start_signal_args=[message],
            )
        else:
            # Send signal to existing workflow
            workflow_handle = client.get_workflow_handle(workflow_id)
            await workflow_handle.signal("user_prompt", message)
        
        # Wait for AI response with configurable timeout
        max_retries = timeout  # Use configurable timeout
        initial_user_count = 0
        initial_response_count = 0
        
        # Get initial counts if not first message
        if not is_first_message:
            try:
                initial_history = await workflow_handle.query("get_conversation_history")
                initial_user_count = len([msg for speaker, msg in initial_history if speaker == "user"])
                initial_response_count = len([msg for speaker, msg in initial_history if speaker == "response"])
            except Exception:
                pass
        
        # Wait for response
        for attempt in range(max_retries):
            try:
                history = await workflow_handle.query("get_conversation_history")
                
                user_messages = [msg for speaker, msg in history if speaker == "user"]
                response_messages = [msg for speaker, msg in history if speaker == "response"]
                
                # For first message, wait for at least one response
                if is_first_message:
                    if len(response_messages) >= 1:
                        break
                else:
                    # For subsequent messages, wait for new response
                    if len(response_messages) > initial_response_count:
                        break
                
                await asyncio.sleep(1.0)
            except Exception as e:
                # On query error, still wait and retry
                await asyncio.sleep(1.0)
                if attempt == max_retries - 1:
                    raise e
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Final validation - ensure we got a response
        try:
            final_history = await workflow_handle.query("get_conversation_history")
            final_user_count = len([msg for speaker, msg in final_history if speaker == "user"])
            final_response_count = len([msg for speaker, msg in final_history if speaker == "response"])
            
            success = final_response_count >= final_user_count
        except Exception:
            success = response_time < timeout  # Fallback success criteria
        
        return {
            'workflow_id': workflow_id,
            'message': message,
            'response_time': response_time,
            'success': success,
            'timestamp': datetime.now()
        }
        
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        
        return {
            'workflow_id': workflow_id,
            'message': message,
            'response_time': response_time,
            'success': False,
            'error': str(e),
            'timestamp': datetime.now()
        }


async def complete_session(client, session_id):
    """Complete a session gracefully."""
    try:
        workflow_handle = client.get_workflow_handle(session_id)
        await workflow_handle.signal("complete_session")
        
        # Wait for completion with timeout
        try:
            await asyncio.wait_for(workflow_handle.result(), timeout=30.0)
            return True
        except asyncio.TimeoutError:
            return False
            
    except Exception:
        return False


async def run_session(client, session_id, user_id, messages, timeout=60):
    """Run a complete session with sequential message handling."""
    session_short_id = session_id.split('_')[-1]  # Get short ID for display
    print(f"🔄 Starting session: {session_short_id}")
    
    results = []
    session_start_time = time.time()
    
    for i, message in enumerate(messages, 1):
        message_preview = f"{message[:50]}{'...' if len(message) > 50 else ''}"
        print(f"  📤 Message {i}/{len(messages)}: {message_preview}")
        
        is_first = (i == 1)
        result = await send_message_to_session(
            client, session_id, message, user_id, is_first, timeout
        )
        results.append(result)
        
        if result['success']:
            print(f"     ✅ Response in {result['response_time']:.2f}s")
        else:
            error_msg = result.get('error', 'Unknown error')[:40]
            print(f"     ❌ Failed: {error_msg}")
            # Continue with next message even on failure
    
    # Complete the session
    print(f"  🏁 Completing session {session_short_id}")
    completion_success = await complete_session(client, session_id)
    
    session_end_time = time.time()
    total_session_time = session_end_time - session_start_time
    
    return {
        'session_id': session_id,
        'user_id': user_id,
        'results': results,
        'completed': completion_success,
        'total_time': total_session_time
    }


async def test_scalability(args):
    """Main scalability test with configurable concurrent sessions."""
    print("🚀 Enhanced Scalability Test - Agent-Based Tool Selection")
    print("=" * 70)
    print(f"⏰ Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"☁️ Temporal Cloud: {cloud_config.TEMPORAL_CLOUD_NAMESPACE}")
    print()
    
    # Test messages that exercise the agent-based tool selection (5 messages)
    test_messages = [
        "Find software development companies in California",           # Company search
        "What's the latest news about AI and machine learning?",      # Web search  
        "I need suppliers for cloud infrastructure services",        # Company search
        "What's the current stock price of Microsoft today?",        # Web search
        "Hello, can you help me understand how this system works?"   # Regular chat
    ]
    
    # Use only the requested number of messages
    messages_to_use = test_messages[:args.messages]
    
    print(f"📋 Test Configuration:")
    print(f"   • Sessions: {args.sessions} concurrent sessions")
    print(f"   • Messages per session: {len(messages_to_use)}")
    print(f"   • Total messages: {args.sessions * len(messages_to_use)}")
    print(f"   • Timeout per message: {args.timeout} seconds")
    print(f"   • Tool mix: Company search, Web search, Regular chat")
    print()
    
    # Validate configuration
    try:
        cloud_config.validate()
        print("✅ Configuration validated")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return
    
    # Connect to Temporal
    try:
        client = await Client.connect(**cloud_config.get_temporal_connection_config())
        print("✅ Connected to Temporal Cloud")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Create configured number of sessions
    sessions = []
    for i in range(args.sessions):
        session_id = f"scale_test_{uuid.uuid4().hex[:8]}_s{i+1:03d}"
        user_id = None  # Use None for testing to avoid foreign key constraint
        sessions.append((session_id, user_id, messages_to_use))
    
    print(f"🆔 Session IDs (showing first 5):")
    for session_id, user_id, _ in sessions[:5]:
        short_id = session_id.split('_')[-1]
        print(f"   • {short_id} (User: {user_id})")
    if len(sessions) > 5:
        print(f"   ... and {len(sessions) - 5} more sessions")
    print()
    
    print("⚠️  Make sure worker is running: python worker_cloud.py")
    print(f"🚀 Starting {args.sessions} concurrent sessions...")
    print()
    
    # Start all sessions concurrently
    start_time = time.time()
    
    tasks = [
        run_session(client, session_id, user_id, messages, args.timeout)
        for session_id, user_id, messages in sessions
    ]
    
    # Run all sessions in parallel
    session_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n✅ All sessions completed in {total_time:.2f} seconds")
    print()
    
    # Process results
    successful_sessions = []
    failed_sessions = []
    all_message_results = []
    
    for i, result in enumerate(session_results):
        if isinstance(result, Exception):
            print(f"❌ Session {i+1} failed: {result}")
            failed_sessions.append(f"session-{i+1}")
        else:
            successful_sessions.append(result)
            all_message_results.extend(result['results'])
    
    # Analysis
    print("📊 Results Analysis")
    print("-" * 40)
    
    total_messages = len(all_message_results)
    successful_messages = sum(1 for r in all_message_results if r['success'])
    failed_messages = total_messages - successful_messages
    
    print(f"📈 Sessions: {len(successful_sessions)}/{len(sessions)} successful ({len(successful_sessions)/len(sessions)*100:.1f}%)")
    print(f"📨 Messages: {successful_messages}/{total_messages} successful")
    print(f"📊 Success rate: {(successful_messages/total_messages)*100:.1f}%" if total_messages > 0 else "📊 Success rate: 0%")
    print(f"⚡ Throughput: {successful_messages/total_time:.2f} messages/second")
    print(f"⏱️  Total test time: {total_time:.2f} seconds")
    
    # Response time analysis
    successful_times = [r['response_time'] for r in all_message_results if r['success']]
    
    if successful_times:
        print(f"⏱️  Response Times:")
        print(f"   • Average: {statistics.mean(successful_times):.3f}s")
        print(f"   • Minimum: {min(successful_times):.3f}s")
        print(f"   • Maximum: {max(successful_times):.3f}s")
        print(f"   • Median: {statistics.median(successful_times):.3f}s")
        
        if len(successful_times) > 1:
            print(f"   • Std Dev: {statistics.stdev(successful_times):.3f}s")
    
    print()
    
    # Per-session breakdown (show sample for large session counts)
    if args.sessions <= 10:
        print("🔍 Per-Session Breakdown:")
        sessions_to_show = successful_sessions
    else:
        print(f"🔍 Per-Session Breakdown (showing first 20 of {len(successful_sessions)} successful):")
        sessions_to_show = successful_sessions[:20]
    
    for session_result in sessions_to_show:
        session_id = session_result['session_id'] 
        short_id = session_id.split('_')[-1]
        results = session_result['results']
        completed = session_result['completed']
        total_session_time = session_result.get('total_time', 0)
        
        session_success_count = sum(1 for r in results if r['success'])
        session_success_rate = (session_success_count / len(results)) * 100
        
        session_times = [r['response_time'] for r in results if r['success']]
        session_avg_time = statistics.mean(session_times) if session_times else 0
        
        print(f"   📋 {short_id}")
        print(f"      ✅ Success: {session_success_count}/{len(results)} ({session_success_rate:.1f}%)")
        print(f"      ⏱️  Avg response time: {session_avg_time:.3f}s")
        print(f"      🕐 Total session time: {total_session_time:.2f}s")
        print(f"      🏁 Completed: {'Yes' if completed else 'No'}")
    
    if args.sessions > 10 and len(successful_sessions) > 20:
        print(f"   ... and {len(successful_sessions) - 20} more successful sessions")
    
    print()
    
    # Tool usage analysis
    print("🛠️  Expected Tool Usage Analysis:")
    company_messages = [msg for msg in messages_to_use if any(word in msg.lower() 
                       for word in ['companies', 'suppliers', 'contractors', 'find'])]
    web_messages = [msg for msg in messages_to_use if any(word in msg.lower() 
                   for word in ['news', 'latest', 'current', 'stock', 'today'])]
    chat_messages = [msg for msg in messages_to_use if any(word in msg.lower() 
                    for word in ['hello', 'help', 'understand', 'how'])]
    
    print(f"   🏢 Company search messages: {len(company_messages)} per session")
    print(f"   🌐 Web search messages: {len(web_messages)} per session") 
    print(f"   💬 Regular chat messages: {len(chat_messages)} per session")
    print(f"   🎯 Agent will decide which tools to actually use")
    
    print()
    
    # Scaling recommendations
    print("📈 Scaling Recommendations:")
    if successful_messages > 0:
        current_throughput = successful_messages / total_time
        sessions_multiplier = max(1, args.sessions // 10)
        estimated_capacity = current_throughput * sessions_multiplier
        
        print(f"   • Current throughput: {current_throughput:.2f} msg/s with {args.sessions} sessions")
        print(f"   • Estimated max capacity: ~{estimated_capacity:.0f} msg/s")
        print(f"   • Avg response time: {statistics.mean(successful_times):.2f}s" if successful_times else "   • No successful responses for timing")
        
        if statistics.mean(successful_times) > 10 if successful_times else False:
            print("   ⚠️  Response times are high - consider adding more workers")
        elif (successful_messages/total_messages) < 0.95 if total_messages > 0 else False:
            print("   ⚠️  Success rate is low - check system capacity")
        else:
            print("   ✅ System performing well at this scale")
    
    print()
    print("🎉 Enhanced scalability test completed!")
    print()
    print("💡 Next steps:")
    print(f"   • Scale further: python test_scalability_simple.py --sessions {args.sessions * 2}")
    print("   • Monitor tool selection accuracy with test_interactive.py")
    print("   • Add more workers if response times increase significantly")
    print(f"   • Current test: {args.sessions} sessions × {len(messages_to_use)} messages = {args.sessions * len(messages_to_use)} total")
    
    return {
        'total_time': total_time,
        'sessions_tested': len(sessions),
        'successful_sessions': len(successful_sessions),
        'total_messages': total_messages,
        'successful_messages': successful_messages,
        'success_rate': (successful_messages/total_messages)*100 if total_messages > 0 else 0,
        'throughput': successful_messages/total_time if total_time > 0 else 0,
        'avg_response_time': statistics.mean(successful_times) if successful_times else 0
    }


if __name__ == "__main__":
    # Parse arguments
    args = parse_arguments()
    
    print("🚀 Enhanced Scalability Test for Agent-Based Tool Selection")
    print()
    print("⚠️  IMPORTANT: Make sure the worker is running!")
    print("   Run: python worker_cloud.py")
    print()
    print(f"📊 Test configuration: {args.sessions} sessions, {args.messages} messages each")
    print()
    
    if not args.skip_confirmation:
        try:
            input("Press Enter when worker is ready, or Ctrl+C to cancel...")
            print()
        except KeyboardInterrupt:
            print("\n🛑 Test cancelled by user")
            sys.exit(1)
    
    try:
        asyncio.run(test_scalability(args))
    except KeyboardInterrupt:
        print("\n🛑 Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)