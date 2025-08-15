#!/usr/bin/env python3

import asyncio
import random
import time
import statistics
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from client_cloud import ChatbotCloudClient


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    num_sessions: int = 20
    min_messages_per_session: int = 5
    max_messages_per_session: int = 7
    min_delay_seconds: float = 1.0
    max_delay_seconds: float = 5.0
    response_timeout_seconds: int = 15
    user_id_base: int = 1000


@dataclass
class TestMetrics:
    """Metrics collected during load testing."""
    total_messages_sent: int = 0
    successful_responses: int = 0
    failed_responses: int = 0
    response_times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0


class ChatbotLoadTester:
    """Load tester for chatbot scalability."""
    
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.metrics = TestMetrics()
        self.test_messages = [
            "Hello, how are you today?",
            "What's the weather like?",
            "Can you tell me a joke?",
            "What is artificial intelligence?",
            "How do you work?",
            "What can you help me with?",
            "Tell me about Python programming",
            "What's your favorite color?",
            "Can you solve math problems?",
            "What is machine learning?",
            "Explain quantum computing",
            "What are the benefits of cloud computing?",
            "How does the internet work?",
            "What is blockchain technology?",
            "Tell me about space exploration"
        ]
    
    async def run_session(self, session_id: str, user_id: int) -> List[Tuple[float, bool, str]]:
        """Run a single chat session with multiple messages."""
        client = ChatbotCloudClient()
        session_results = []
        
        # Randomly choose number of messages between min and max
        num_messages = random.randint(self.config.min_messages_per_session, self.config.max_messages_per_session)
        
        try:
            await client.connect()
            print(f"🚀 Starting session {session_id} for user {user_id} ({num_messages} messages)")
            
            for msg_num in range(num_messages):
                message = random.choice(self.test_messages)
                
                # Record start time
                start_time = time.time()
                
                try:
                    # Send message
                    await client.send_message(session_id, message, user_id)
                    
                    # Wait for response (simulate real user behavior)
                    await asyncio.sleep(
                        random.uniform(self.config.min_delay_seconds, self.config.max_delay_seconds)
                    )
                    
                    # Try to get conversation history to verify response
                    history = await client.get_conversation_history(session_id)
                    
                    # Calculate response time
                    response_time = time.time() - start_time
                    
                    # Check if we got a response
                    has_response = len(history) > msg_num * 2  # User + bot messages
                    
                    session_results.append((response_time, has_response, "Success"))
                    
                    if has_response:
                        print(f"✅ Session {session_id} Message {msg_num + 1}: {response_time:.2f}s")
                    else:
                        print(f"⚠️ Session {session_id} Message {msg_num + 1}: No response yet ({response_time:.2f}s)")
                
                except Exception as e:
                    response_time = time.time() - start_time
                    error_msg = f"Error in session {session_id}: {str(e)}"
                    session_results.append((response_time, False, error_msg))
                    print(f"❌ {error_msg}")
                
                # Small delay between messages in the same session
                if msg_num < num_messages - 1:
                    await asyncio.sleep(random.uniform(0.5, 2.0))
        
        finally:
            await client.close()
        
        return session_results
    
    async def run_load_test(self) -> TestMetrics:
        """Run the complete load test with multiple concurrent sessions."""
        avg_messages = (self.config.min_messages_per_session + self.config.max_messages_per_session) / 2
        estimated_total = int(self.config.num_sessions * avg_messages)
        
        print(f"🎯 Starting load test: {self.config.num_sessions} sessions, "
              f"{self.config.min_messages_per_session}-{self.config.max_messages_per_session} messages each")
        print(f"📊 Estimated total messages: ~{estimated_total}")
        
        self.metrics.start_time = time.time()
        
        # Create tasks for all sessions
        tasks = []
        for i in range(self.config.num_sessions):
            session_id = f"load-test-{i+1:02d}"
            user_id = self.config.user_id_base + i
            task = asyncio.create_task(self.run_session(session_id, user_id))
            tasks.append(task)
        
        print(f"⚡ Launching {len(tasks)} concurrent sessions...")
        
        # Wait for all sessions to complete
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            print(f"❌ Error during load test: {e}")
            results = []
        
        self.metrics.end_time = time.time()
        
        # Process results
        for session_results in results:
            if isinstance(session_results, Exception):
                self.metrics.errors.append(str(session_results))
                continue
                
            for response_time, success, error_msg in session_results:
                self.metrics.total_messages_sent += 1
                self.metrics.response_times.append(response_time)
                
                if success:
                    self.metrics.successful_responses += 1
                else:
                    self.metrics.failed_responses += 1
                    if error_msg != "Success":
                        self.metrics.errors.append(error_msg)
        
        return self.metrics
    
    def print_results(self) -> None:
        """Print detailed test results."""
        duration = self.metrics.end_time - self.metrics.start_time
        
        print("\n" + "="*60)
        print("📈 LOAD TEST RESULTS")
        print("="*60)
        
        print(f"⏱️  Total Duration: {duration:.2f} seconds")
        print(f"📨 Messages Sent: {self.metrics.total_messages_sent}")
        print(f"✅ Successful Responses: {self.metrics.successful_responses}")
        print(f"❌ Failed Responses: {self.metrics.failed_responses}")
        print(f"📊 Success Rate: {(self.metrics.successful_responses / max(self.metrics.total_messages_sent, 1)) * 100:.1f}%")
        
        if self.metrics.response_times:
            print(f"\n⚡ Response Time Statistics:")
            print(f"   Average: {statistics.mean(self.metrics.response_times):.2f}s")
            print(f"   Median: {statistics.median(self.metrics.response_times):.2f}s")
            print(f"   Min: {min(self.metrics.response_times):.2f}s")
            print(f"   Max: {max(self.metrics.response_times):.2f}s")
            
            if len(self.metrics.response_times) > 1:
                print(f"   Std Dev: {statistics.stdev(self.metrics.response_times):.2f}s")
        
        print(f"\n🚀 Throughput: {self.metrics.total_messages_sent / duration:.2f} messages/second")
        
        if self.metrics.errors:
            print(f"\n❌ Errors ({len(self.metrics.errors)}):")
            for error in self.metrics.errors[:10]:  # Show first 10 errors
                print(f"   • {error}")
            if len(self.metrics.errors) > 10:
                print(f"   ... and {len(self.metrics.errors) - 10} more errors")


async def main():
    """Run the load test."""
    # Configuration
    config = LoadTestConfig(
        num_sessions=20,
        min_messages_per_session=5,
        max_messages_per_session=7,
        min_delay_seconds=1.0,
        max_delay_seconds=3.0,
        response_timeout_seconds=15,
        user_id_base=2000
    )
    
    # Create and run load tester
    tester = ChatbotLoadTester(config)
    
    try:
        print(f"🔥 Temporal Chatbot Load Test")
        print(f"🎯 Configuration:")
        print(f"   Sessions: {config.num_sessions}")
        print(f"   Messages per session: {config.min_messages_per_session}-{config.max_messages_per_session}")
        print(f"   Delay range: {config.min_delay_seconds}-{config.max_delay_seconds}s")
        print(f"   User ID base: {config.user_id_base}")
        print()
        
        metrics = await tester.run_load_test()
        tester.print_results()
        
        # Return appropriate exit code
        if metrics.failed_responses == 0:
            print(f"\n🎉 Load test completed successfully!")
            return 0
        else:
            print(f"\n⚠️ Load test completed with {metrics.failed_responses} failures")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n🛑 Load test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Load test failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)