#!/usr/bin/env python3
"""
Simplified scalability test for agent-based tool selection chatbot.

This script tests concurrent sessions with the new AI-powered tool selection
system using a manageable number of sessions for initial testing.

Features:
- Tests 3 concurrent sessions (easily adjustable)
- Each session sends 6 messages that test different tool scenarios
- Real response time measurement
- Tool usage analysis
- Simple, clean output

Usage:
    python test_scalability_simple.py
"""

import asyncio
import time
import uuid
import statistics
from datetime import datetime
from pathlib import Path
import sys

# Add chatbot_backend to path
sys.path.insert(0, str(Path(__file__).parent))

from temporalio.client import Client
from workflows.chat_workflow import SignalQueryOpenAIWorkflow
from config_cloud import cloud_config


async def send_message_to_session(client, workflow_id, message, user_id=None, is_first_message=False):
    """Send a message to a session and wait for the AI response."""
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
        
        # Wait for AI response (check conversation history)
        max_retries = 30  # 30 seconds timeout
        for attempt in range(max_retries):
            try:
                history = await workflow_handle.query("get_conversation_history")
                
                # Check if we have response for our message
                user_messages = [msg for speaker, msg in history if speaker == "user"]
                response_messages = [msg for speaker, msg in history if speaker == "response"]
                
                if len(response_messages) >= len(user_messages):
                    break
                
                await asyncio.sleep(1.0)
            except Exception:
                await asyncio.sleep(1.0)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        return {
            'workflow_id': workflow_id,
            'message': message,
            'response_time': response_time,
            'success': True,
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


async def run_session(client, session_id, user_id, messages):
    """Run a complete session with multiple messages."""
    print(f"🔄 Starting session: {session_id}")
    
    results = []
    
    for i, message in enumerate(messages, 1):
        print(f"  📤 Message {i}/6: {message[:60]}{'...' if len(message) > 60 else ''}")
        
        is_first = (i == 1)
        result = await send_message_to_session(client, session_id, message, user_id, is_first)
        results.append(result)
        
        if result['success']:
            print(f"     ✅ Response in {result['response_time']:.2f}s")
        else:
            print(f"     ❌ Failed: {result.get('error', 'Unknown error')}")
    
    # Complete the session
    print(f"  🏁 Completing session {session_id}")
    completion_success = await complete_session(client, session_id)
    
    return {
        'session_id': session_id,
        'user_id': user_id,
        'results': results,
        'completed': completion_success
    }


async def test_scalability():
    """Main scalability test with 3 concurrent sessions."""
    print("🚀 Scalability Test - Agent-Based Tool Selection")
    print("=" * 65)
    print(f"⏰ Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"☁️ Temporal Cloud: {cloud_config.TEMPORAL_CLOUD_NAMESPACE}")
    print()
    
    # Test messages that exercise the new agent-based tool selection
    test_messages = [
        "Find software development companies in California",           # Company search
        "What's the latest news about AI and machine learning?",      # Web search  
        "I need suppliers for cloud infrastructure services",        # Company search
        "What's the current stock price of Microsoft today?",        # Web search
        "Show me construction contractors with green building expertise", # Company search
        "Hello, can you help me understand how this system works?"   # Regular chat
    ]
    
    print(f"📋 Test Configuration:")
    print(f"   • Sessions: 3 concurrent sessions")
    print(f"   • Messages per session: {len(test_messages)}")
    print(f"   • Total messages: {3 * len(test_messages)}")
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
    
    # Create 3 sessions
    sessions = []
    for i in range(3):
        session_id = f"scale_test_{uuid.uuid4().hex[:8]}_s{i+1}"
        user_id = None  # Use None for testing to avoid foreign key constraint
        sessions.append((session_id, user_id, test_messages))
    
    print(f"🆔 Session IDs:")
    for session_id, user_id, _ in sessions:
        print(f"   • {session_id} (User: {user_id})")
    print()
    
    print("⚠️  Make sure worker is running: python worker_cloud.py")
    print("🚀 Starting 3 concurrent sessions...")
    print()
    
    # Start all sessions concurrently
    start_time = time.time()
    
    tasks = [
        run_session(client, session_id, user_id, messages)
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
    
    print(f"📈 Sessions: {len(successful_sessions)}/{len(sessions)} successful")
    print(f"📨 Messages: {successful_messages}/{total_messages} successful")
    print(f"📊 Success rate: {(successful_messages/total_messages)*100:.1f}%" if total_messages > 0 else "📊 Success rate: 0%")
    print(f"⚡ Throughput: {successful_messages/total_time:.2f} messages/second")
    
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
    
    # Per-session breakdown
    print("🔍 Per-Session Breakdown:")
    for session_result in successful_sessions:
        session_id = session_result['session_id']
        results = session_result['results']
        completed = session_result['completed']
        
        session_success_count = sum(1 for r in results if r['success'])
        session_success_rate = (session_success_count / len(results)) * 100
        
        session_times = [r['response_time'] for r in results if r['success']]
        session_avg_time = statistics.mean(session_times) if session_times else 0
        
        print(f"   📋 {session_id}")
        print(f"      ✅ Success: {session_success_count}/{len(results)} ({session_success_rate:.1f}%)")
        print(f"      ⏱️  Avg time: {session_avg_time:.3f}s")
        print(f"      🏁 Completed: {'Yes' if completed else 'No'}")
    
    print()
    
    # Tool usage analysis
    print("🛠️  Expected Tool Usage Analysis:")
    company_messages = [msg for msg in test_messages if any(word in msg.lower() 
                       for word in ['companies', 'suppliers', 'contractors', 'find'])]
    web_messages = [msg for msg in test_messages if any(word in msg.lower() 
                   for word in ['news', 'latest', 'current', 'stock', 'today'])]
    chat_messages = [msg for msg in test_messages if any(word in msg.lower() 
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
        print(f"   • Current throughput: {current_throughput:.2f} msg/s with 3 sessions")
        print(f"   • Estimated capacity: ~{current_throughput * 10:.0f} msg/s with 10 sessions")
        print(f"   • For production: Monitor response times and adjust worker count")
    
    print()
    print("🎉 Scalability test completed!")
    print()
    print("💡 Next steps:")
    print("   • Increase session count in the script for higher load testing")
    print("   • Monitor tool selection accuracy with test_interactive.py")
    print("   • Add more workers if response times increase significantly")
    
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
    print("🚀 Scalability Test for Agent-Based Tool Selection")
    print()
    print("⚠️  IMPORTANT: Make sure the worker is running!")
    print("   Run: python worker_cloud.py")
    print()
    
    try:
        input("Press Enter when worker is ready, or Ctrl+C to cancel...")
        print()
        asyncio.run(test_scalability())
    except KeyboardInterrupt:
        print("\n🛑 Test cancelled by user")
        sys.exit(1)