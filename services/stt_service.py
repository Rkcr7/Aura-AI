import asyncio
import httpx
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
from core.config import settings

async def verify_deepgram_api_key():
    """
    Verifies the Deepgram API key by making a direct HTTP request.
    This is the most reliable method, independent of SDK changes.
    Returns True if the key is valid, False otherwise.
    """
    if not settings.DEEPGRAM_API_KEY:
        return False

    url = "https://api.deepgram.com/v1/projects"
    headers = {
        "Authorization": f"Token {settings.DEEPGRAM_API_KEY}"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                print("INFO: Deepgram API key is valid.")
                return True
            else:
                print(f"ERROR: Deepgram API key verification failed. Status: {response.status_code}, Response: {response.text}")
                return False
    except httpx.RequestError as e:
        print(f"ERROR: A network error occurred while verifying Deepgram key: {e}")
        return False


class DeepgramManager:
    """
    Manages the connection to Deepgram for live transcription.
    """
    def __init__(self, transcript_callback, user_languages=None):
        self.transcript_callback = transcript_callback
        self.dg_connection = None
        self.is_connected = False
        self.stop_event = asyncio.Event()
        self.user_languages = user_languages or []
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_base_delay = 1.0  # seconds
        
        # No buffering - process final results immediately for faster response
        
        # Setup Deepgram client
        config = DeepgramClientOptions(
            verbose=False,  # Disable verbose logging to reduce spam
            options={"keepalive": "true"}
        )
        self.deepgram = DeepgramClient(settings.DEEPGRAM_API_KEY, config)

    def get_programming_keyterms(self, user_languages=None):
        """
        Generate programming and technical keyterms for better speech recognition.
        Limited to 500 tokens as per Deepgram requirements.
        Prioritizes terms based on user's selected programming languages.
        """
        # Core programming concepts and algorithms
        keyterms = [
            # LeetCode and coding platforms
            "LeetCode", "leetcode", "LeetCode problem", "HackerRank", "CodeSignal", "Codility",
            "coding interview", "technical interview", "whiteboard", "online judge",
            
            # Common algorithm problems (with variations)
            "two sum", "2sum", "two-sum", "three sum", "3sum", "three-sum", 
            "four sum", "4sum", "four-sum", "valid parentheses", "merge intervals",
            "climbing stairs", "house robber", "coin change", "longest substring",
            "palindrome", "reverse linked list", "binary tree traversal",
            "binary search", "depth first search", "DFS", "breadth first search", "BFS",
            "dynamic programming", "DP", "greedy algorithm", "backtracking",
            "sliding window", "two pointers", "fast slow pointers",
            
            # Data structures
            "linked list", "binary tree", "binary search tree", "BST",
            "hash map", "hash table", "hash set", "array", "stack", "queue",
            "heap", "priority queue", "trie", "graph", "adjacency list",
            "adjacency matrix", "disjoint set", "union find",
            
            # Programming languages
            "Python", "Java", "JavaScript", "TypeScript", "C++", "C sharp",
            "Go", "Rust", "Swift", "Kotlin", "Scala", "Ruby", "PHP",
            
            # Common programming terms (with pronunciation variations)
            "algorithm", "algorithms", "complexity", "time complexity", "space complexity",
            "Big O", "big oh", "O of n", "O of log n", "O of n squared", "O of 1", "O one",
            "recursion", "recursive", "iteration", "iterative", "memoization", "tabulation",
            "optimization", "optimize", "brute force", "optimal solution", "suboptimal",
            "amortized", "worst case", "best case", "average case",
            
            # Technical interview terms
            "edge case", "corner case", "test case", "unit test",
            "refactor", "optimize", "debug", "runtime", "memory",
            "scalability", "performance", "bottleneck",
            
            # Common coding patterns
            "singleton", "factory", "observer", "decorator", "adapter",
            "strategy", "command", "facade", "proxy", "builder",
            
            # Database and system design
            "SQL", "NoSQL", "database", "schema", "index", "query",
            "JOIN", "LEFT JOIN", "INNER JOIN", "GROUP BY", "ORDER BY",
            "API", "REST", "GraphQL", "microservices", "monolith",
            "load balancer", "cache", "Redis", "MongoDB", "PostgreSQL",
            
            # Web development
            "React", "Angular", "Vue", "Node.js", "Express", "Django",
            "Flask", "Spring", "HTML", "CSS", "DOM", "JSON", "XML",
            "HTTP", "HTTPS", "GET", "POST", "PUT", "DELETE",
            
            # Common technical terms
            "variable", "function", "method", "class", "object", "instance",
            "inheritance", "polymorphism", "encapsulation", "abstraction",
            "interface", "abstract", "static", "final", "const", "let", "var",
            "async", "await", "promise", "callback", "closure", "scope",
            
            # Numbers and common values
            "zero", "one", "two", "three", "four", "five", "null", "undefined",
            "true", "false", "boolean", "integer", "string", "float", "double"
        ]
        
        # Prioritize keyterms based on user's selected languages
        prioritized_keyterms = []
        
        # Add user's selected languages first (higher priority)
        if user_languages:
            for lang in user_languages:
                lang_lower = lang.lower()
                # Add language-specific terms first
                if lang_lower == 'python':
                    prioritized_keyterms.extend(['Python', 'Django', 'Flask', 'pandas', 'numpy', 'pip', 'virtualenv'])
                elif lang_lower == 'java':
                    prioritized_keyterms.extend(['Java', 'Spring', 'Maven', 'Gradle', 'JVM', 'JDK', 'servlet'])
                elif lang_lower == 'javascript':
                    prioritized_keyterms.extend(['JavaScript', 'Node.js', 'React', 'Vue', 'Angular', 'npm', 'webpack'])
                elif lang_lower == 'typescript':
                    prioritized_keyterms.extend(['TypeScript', 'interface', 'type', 'generic', 'decorator'])
                elif lang_lower == 'c++':
                    prioritized_keyterms.extend(['C++', 'STL', 'vector', 'iterator', 'template', 'namespace'])
                elif lang_lower == 'sql':
                    prioritized_keyterms.extend(['SQL', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'JOIN', 'WHERE'])
        
        # Add general programming terms
        prioritized_keyterms.extend(keyterms)
        
        # Remove duplicates while preserving order
        seen = set()
        final_keyterms = []
        for term in prioritized_keyterms:
            if term not in seen:
                seen.add(term)
                final_keyterms.append(term)
        
        # Join keyterms with proper URL encoding for multiple keyterms
        # Using space separation as recommended by Deepgram for phrase boosting
        # Limit to ensure we stay under 500 token limit (roughly 80-85 terms)
        keyterm_string = " ".join(final_keyterms[:85])  # Conservative limit to stay under 500 tokens
        
        print(f"🔧 Programming keyterms configured: {len(final_keyterms[:85])} terms")
        if user_languages:
            print(f"🎯 Prioritized for languages: {', '.join(user_languages)}")
        print(f"📝 Sample keyterms: {', '.join(final_keyterms[:10])}...")
        
        return keyterm_string

    async def start(self):
        """Starts the Deepgram transcription connection."""
        self.dg_connection = self.deepgram.listen.asynclive.v("1")
        
        self.dg_connection.on(LiveTranscriptionEvents.Open, self.on_open)
        self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.on_message)
        self.dg_connection.on(LiveTranscriptionEvents.Error, self.on_error)
        self.dg_connection.on(LiveTranscriptionEvents.Close, self.on_close)

        # Generate programming and technical keyterms for better accuracy
        programming_keyterms = self.get_programming_keyterms(self.user_languages)
        
        # Optimized settings for real-time transcription with Nova-3
        options = LiveOptions(
            model="nova-3",  # Updated to Nova-3 for better accuracy
            language="en",
            smart_format=True,
            encoding="linear16",
            channels=1,
            sample_rate=48000,  # Pinned client-side by TARGET_SAMPLE_RATE in web/js/audio_handler.js
            diarize=False,
            punctuate=True,
            # Critical speech detection parameters
            utterance_end_ms=1000,    # Wait 1.2 seconds after speech ends to finalize
            endpointing=600,          # Wait 0.8 seconds of silence before endpoint detection
            # Additional settings
            vad_events=True,          # Enable VAD for better pause handling
            interim_results=True,     # Enable interim results for real-time feedback
            filler_words=True,        # Handle filler words naturally
            numerals=True,            # Better number processing
            multichannel=False,
            alternatives=1,
            # Programming keyterms for better technical accuracy
            keyterm=programming_keyterms,
        )
        
        try:
            await self.dg_connection.start(options)
            self.is_connected = True
            self._reconnect_attempts = 0  # Reset on successful connect
            print("✅ Deepgram connection started successfully")
        except Exception as e:
            print(f"❌ ERROR: Could not start Deepgram connection: {e}")

    async def _reconnect(self):
        """Attempt to reconnect to Deepgram with exponential backoff."""
        if self.stop_event.is_set():
            return
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            print(f"❌ Deepgram: max reconnect attempts ({self._max_reconnect_attempts}) reached, giving up")
            return

        self._reconnect_attempts += 1
        delay = self._reconnect_base_delay * (2 ** (self._reconnect_attempts - 1))
        print(f"🔄 Deepgram reconnect attempt {self._reconnect_attempts}/{self._max_reconnect_attempts} in {delay:.1f}s...")
        await asyncio.sleep(delay)

        if self.stop_event.is_set():
            return

        try:
            await self.start()
            print(f"✅ Deepgram reconnected after {self._reconnect_attempts} attempt(s)")
        except Exception as e:
            print(f"❌ Deepgram reconnect failed: {e}")
            asyncio.create_task(self._reconnect())

    async def on_open(self, *args, **kwargs):
        print("🔗 Deepgram connection opened")
        self.is_connected = True

    async def on_message(self, *args, **kwargs):
        if self.stop_event.is_set():
            return
        
        try:
            result = kwargs['result']
            
            # Check if result has the expected structure and non-empty transcript
            if (hasattr(result, 'channel') and 
                hasattr(result.channel, 'alternatives') and 
                len(result.channel.alternatives) > 0):
                
                alternative = result.channel.alternatives[0]
                transcript = alternative.transcript
                
                if len(transcript.strip()) > 0:  # Only process non-empty transcripts
                    # Check if this is a final result or interim
                    is_final = getattr(result, 'is_final', True)
                    
                    # Debug logging to track final vs interim
                    result_type = "FINAL" if is_final else "interim"
                    print(f"🔍 Deepgram result type: {result_type}, is_final: {is_final}")
                    
                    # Get speaker from words array (Deepgram's diarization format)
                    speaker = 0  # Default to candidate (when diarization is disabled, all speech is from speaker 0)
                    
                    # Only try to extract speaker info if diarization was enabled
                    # When diarization is disabled, Deepgram doesn't provide speaker information
                    try:
                        if hasattr(alternative, 'words') and len(alternative.words) > 0:
                            # Use the speaker of the first word
                            first_word = alternative.words[0]
                            if hasattr(first_word, 'speaker') and first_word.speaker is not None:
                                speaker = first_word.speaker
                            elif hasattr(first_word, '__getitem__') and 'speaker' in first_word:
                                # Fallback: try to access speaker as dictionary key
                                speaker = first_word['speaker']
                    except (AttributeError, KeyError, IndexError):
                        # If any error occurs accessing speaker info, stick with default (speaker 0)
                        # This is expected when diarization is disabled
                        pass
                    
                    if is_final:
                        # Process final results immediately - no buffering
                        print(f"✅ FINAL RESULT: Speaker {speaker} - '{transcript.strip()}'")
                        await self.send_final_result(speaker, transcript.strip())
                    else:
                        # Show interim results immediately for real-time feedback
                        print(f"📝 TRANSCRIPT (interim): Speaker {speaker} - '{transcript.strip()}'")
                        
                        # Send interim updates to client for real-time display
                        interim_data = {
                            "speaker": speaker,
                            "transcript": transcript.strip(),
                            "is_final": False
                        }
                        await self.transcript_callback(interim_data)
                        
        except Exception as e:
            print(f"❌ ERROR: Exception in transcript processing: {e}")

    # Removed buffering system - final results are now processed immediately

    async def send_final_result(self, speaker, transcript):
        """Send the final result to the callback."""
        print(f"📝 TRANSCRIPT (FINAL): Speaker {speaker} - '{transcript}'")
        
        transcript_data = {
            "speaker": speaker,
            "transcript": transcript,
            "is_final": True
        }
        await self.transcript_callback(transcript_data)

    async def on_error(self, *args, **kwargs):
        if self.stop_event.is_set():
            return
        error = kwargs.get('error', 'unknown')
        print(f"❌ Deepgram error: {error}")
        self.is_connected = False
        # Trigger auto-reconnect on error
        asyncio.create_task(self._reconnect())

    async def on_close(self, *args, **kwargs):
        print("🔌 Deepgram connection closed")
        self.is_connected = False
        # Auto-reconnect if we didn't intentionally close
        if not self.stop_event.is_set():
            print("⚠️ Unexpected Deepgram close, attempting reconnect...")
            asyncio.create_task(self._reconnect())

    async def send_audio(self, audio_chunk, source='unknown'):
        """Sends an audio chunk to Deepgram."""
        if self.is_connected and self.dg_connection and not self.stop_event.is_set():
            await self.dg_connection.send(audio_chunk)

    async def finish(self):
        """Signals the connection to close and finishes it."""
        print("🛑 Closing Deepgram connection...")
        self.stop_event.set()
        
        if self.dg_connection:
            await self.dg_connection.finish()
            print("✅ Deepgram connection closed successfully")