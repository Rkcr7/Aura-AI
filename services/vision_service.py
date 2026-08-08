import orjson
import asyncio
import base64
import threading
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from openai import AsyncOpenAI, APIStatusError
from core.config import settings
from core.key_utils import usable_keys

class VisionManager:
    """Vision AI Manager for screenshot analysis and code problem solving"""
    
    def __init__(self, provider_name: str, base_url: str, api_key: str, model_name: str, request_params: Optional[Dict[str, Any]] = None, api_keys: Optional[List[str]] = None):
        self.provider_name = provider_name
        self.model_name = model_name
        self.base_url = base_url
        self.request_params = request_params or {}
        self.is_healthy = True
        self.last_error = None
        self.error_count = 0
        self.last_success_time = datetime.now()
        self.context_manager = None  # Will be set by VisionService
        
        # Key rotation support — drop blank/placeholder entries so a half-filled
        # config (real "apiKey" + untouched "apiKeys" placeholders) still works.
        self.api_keys = usable_keys(api_keys) or usable_keys([api_key]) or [""]
        if not self.api_keys[0]:
            print(f"⚠️ No usable vision API key for {provider_name} — set 'apiKey' or 'apiKeys' in ai_providers.json")
        self.api_key = self.api_keys[0]
        self._key_index = 0
        self._key_lock = threading.Lock()
        self._request_count = 0
        
        try:
            self.client = AsyncOpenAI(base_url=base_url, api_key=self.api_key)
            print(f"✅ VisionManager initialized for: {self.provider_name} - {self.model_name} ({len(self.api_keys)} keys available)")
        except Exception as e:
            self.client = None
            self.is_healthy = False
            self.last_error = str(e)
            print(f"❌ CRITICAL: Failed to initialize VisionManager for {self.provider_name}: {e}")

    def _rotate_key(self):
        """Rotate to the next API key using round-robin."""
        if len(self.api_keys) <= 1:
            return
        with self._key_lock:
            self._key_index = (self._key_index + 1) % len(self.api_keys)
            self.api_key = self.api_keys[self._key_index]
            self.client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
            self._request_count += 1
            print(f"🔑 Vision key rotation [{self.provider_name}]: using key index {self._key_index}/{len(self.api_keys)}")

    def set_context_manager(self, context_manager):
        """Set the shared context manager"""
        self.context_manager = context_manager

    async def health_check(self) -> bool:
        """Check if the vision provider is healthy and responsive"""
        if not self.client:
            return False
            
        try:
            # Quick test call to verify connectivity
            await asyncio.wait_for(self.client.models.list(), timeout=5.0)
            self.is_healthy = True
            self.error_count = 0
            self.last_success_time = datetime.now()
            return True
        except asyncio.TimeoutError:
            self.is_healthy = False
            self.last_error = "Connection timeout"
            self.error_count += 1
            return False
        except Exception as e:
            self.is_healthy = False
            self.last_error = str(e)
            self.error_count += 1
            return False

    async def analyze_screenshots(self, prompt: str, screenshots: List[str], languages: List[str] = None) -> Tuple[str, Dict[str, Any]]:
        """Analyze screenshots with instant key rotation on any error — zero delay retries."""
        if not self.client:
            return "I'm sorry, the vision AI service is not available at this time.", {
                "error": "No client available",
                "provider": self.provider_name,
                "model": self.model_name
            }
        
        # Prepare the message content with text and images (once, before retry loop)
        content = [{"type": "text", "text": prompt}]
        for i, screenshot_data_url in enumerate(screenshots):
            if not screenshot_data_url.startswith('data:image/'):
                screenshot_data_url = f"data:image/jpeg;base64,{screenshot_data_url}"
            content.append({
                "type": "image_url",
                "image_url": {"url": screenshot_data_url}
            })
        
        print(f"🔍 Analyzing {len(screenshots)} screenshots with {self.provider_name}-{self.model_name}")
        
        # Try all available keys — instant retry on any error
        max_attempts = len(self.api_keys)
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                # Rotate key for each attempt (first attempt uses current key)
                if attempt > 0:
                    self._rotate_key()
                    print(f"🔄 Vision instant retry attempt {attempt+1}/{max_attempts} with next key for {self.provider_name}")
                
                # Build API params
                api_params = {
                    "messages": [{"role": "user", "content": content}],
                    "model": self.model_name,
                    "temperature": 0.45,
                    "max_tokens": 8100,
                    "top_p": 0.95
                }

                # Add provider-specific routing if available
                if self.request_params:
                    if self.provider_name == "OpenRouter" and "provider" in self.request_params:
                        api_params["extra_body"] = self.request_params
                    else:
                        api_params.update(self.request_params)
                
                # Make API call
                chat_completion = await asyncio.wait_for(
                    self.client.chat.completions.create(**api_params),
                    timeout=75.0
                )
                
                analysis = chat_completion.choices[0].message.content.strip()
                
                # Add vision analysis to conversation history if context manager available
                if self.context_manager:
                    self.context_manager.add_ai_response(analysis, "vision")
                
                # Success!
                self.is_healthy = True
                self.error_count = 0
                self.last_success_time = datetime.now()
                
                return analysis, {
                    "success": True,
                    "provider": self.provider_name,
                    "model": self.model_name,
                    "key_rotated": attempt > 0,
                    "attempt": attempt + 1,
                    "screenshot_count": len(screenshots),
                    "languages": languages or [],
                    "response_time": datetime.now().isoformat(),
                    "analysis_length": len(analysis)
                }
                
            except Exception as e:
                last_error = e
                err_str = str(e)[:100]
                print(f"⚡ Vision key #{self._key_index} failed for {self.provider_name}: {err_str}")
                # Continue to next key immediately — no delay
                continue
        
        # All keys exhausted
        error_msg = f"All {max_attempts} vision keys failed for {self.provider_name}. Last error: {str(last_error)[:100]}"
        self.is_healthy = False
        self.last_error = str(last_error)
        self.error_count += 1
        print(f"🚨 ALL VISION KEYS EXHAUSTED: {self.provider_name}-{self.model_name}")
        
        return error_msg, {
            "error": "all_keys_failed",
            "attempts": max_attempts,
            "provider": self.provider_name,
            "model": self.model_name,
            "screenshot_count": len(screenshots)
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current status of this vision manager"""
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "is_healthy": self.is_healthy,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "last_success": self.last_success_time.isoformat() if self.last_success_time else None,
            "supports_vision": True
        }

class VisionService:
    """Service for managing vision analysis requests and providers"""
    
    def __init__(self):
        self.vision_managers: Dict[str, VisionManager] = {}
        self.active_vision_providers: Dict[str, VisionManager] = {}
        self.context_manager = None

    def set_context_manager(self, context_manager):
        """Set the shared context manager for all vision managers"""
        self.context_manager = context_manager
        # Update all existing vision managers
        for manager in self.vision_managers.values():
            manager.set_context_manager(context_manager)
        
    def load_vision_providers(self, primary_config: Optional[Dict] = None, secondary_config: Optional[Dict] = None) -> bool:
        """Load active vision providers based on user selection."""
        self.active_vision_providers = {}
        
        if primary_config and primary_config.get('provider') and primary_config.get('model'):
            manager = self._create_vision_manager(primary_config['provider'], primary_config['model'])
            if manager:
                self.active_vision_providers['primary'] = manager

        if secondary_config and secondary_config.get('provider') and secondary_config.get('model'):
            manager = self._create_vision_manager(secondary_config['provider'], secondary_config['model'])
            if manager:
                self.active_vision_providers['secondary'] = manager
        
        print(f"✅ VisionService configured with {len(self.active_vision_providers)} active vision models.")
        return len(self.active_vision_providers) > 0

    def _create_vision_manager(self, provider_name: str, model_name: str) -> Optional[VisionManager]:
        """Create and return a vision manager for a given provider and model."""
        try:
            with open("ai_providers.json", "rb") as f:
                providers_config = orjson.loads(f.read())

            for provider_config in providers_config:
                if provider_config["name"] == provider_name:
                    # Find the model configuration, supporting both string and dict formats
                    model_config = self._get_vision_model_config(provider_config, model_name)
                    
                    manager = VisionManager(
                        provider_name=provider_name,
                        base_url=provider_config["baseURL"],
                        api_key=provider_config.get("apiKey", ""),
                        model_name=model_config["modelName"],
                        request_params=model_config.get("requestParams"),
                        api_keys=provider_config.get("apiKeys")
                    )
                    if self.context_manager:
                        manager.set_context_manager(self.context_manager)
                    return manager
            return None
        except Exception as e:
            print(f"❌ Failed to create vision manager for {provider_name}: {e}")
            return None

    def _get_vision_model_config(self, provider_config: Dict[str, Any], model_identifier: str) -> Dict[str, Any]:
        """Finds vision model configuration, supporting both string and dict formats."""
        for model in provider_config.get("visionModels", []):
            if isinstance(model, str) and model == model_identifier:
                return {"modelName": model}  # Normalize to dict
            if isinstance(model, dict) and model.get("modelName") == model_identifier:
                return model
        raise ValueError(f"Vision model '{model_identifier}' not found for provider '{provider_config['name']}'")
    
    def get_vision_manager(self, provider_name: str, model_name: str) -> Optional[VisionManager]:
        """Get a specific vision manager, checking active providers first."""
        # Check active providers first
        for key, manager in self.active_vision_providers.items():
            if manager.provider_name == provider_name and manager.model_name == model_name:
                return manager
        
        # Fallback to creating a new one if not found in active
        print(f"⚠️ Vision manager for {provider_name} - {model_name} not found in active providers. Creating on-the-fly.")
        return self._create_vision_manager(provider_name, model_name)
    
    async def analyze_coding_problem(self, provider_name: str, model_name: str, 
                                   screenshots: List[str], languages: List[str] = None) -> Tuple[str, Dict[str, Any]]:
        """Analyze coding problem screenshots with comprehensive prompting"""
        
        vision_manager = self.get_vision_manager(provider_name, model_name)
        if not vision_manager:
            return f"Vision model {provider_name} - {model_name} not available.", {
                "error": "vision_model_not_found",
                "provider": provider_name,
                "model": model_name
            }
        
        # Generate comprehensive coding prompt
        prompt = self.generate_coding_analysis_prompt(languages)
        
        # Perform vision analysis
        return await vision_manager.analyze_screenshots(prompt, screenshots, languages)
    
    def generate_coding_analysis_prompt(self, languages: List[str] = None) -> str:
        """Generate a comprehensive prompt for analyzing screenshots, capable of handling coding problems, MCQs, or a mix."""
        
        # Determine primary programming language and context
        primary_language = "Java"  # Default fallback
        language_context = ""
        sql_available = False
        
        if languages and len(languages) > 0:
            programming_languages = [lang for lang in languages if lang.lower() != 'sql']
            sql_available = 'sql' in [lang.lower() for lang in languages]
            
            if programming_languages:
                primary_language = programming_languages[0]
                other_languages = programming_languages[1:] if len(programming_languages) > 1 else []
                
                language_context = f"**Primary Programming Language (if applicable for coding/MCQs):** {primary_language}\\n"
                if other_languages:
                    language_context += f"**Alternative Languages:** {', '.join(other_languages)}\\n"
            elif sql_available: # Only SQL was selected
                language_context = f"**Primary Programming Language (default for coding tasks):** {primary_language}\\n**Database Language Detected:** SQL\\n"
            else: # No languages or only non-SQL, non-programming specified
                language_context = f"**Primary Programming Language (default for coding tasks):** {primary_language}\\n"
        else:
            language_context = f"**Primary Programming Language (default for coding tasks):** {primary_language}\\n"

        # Conditional SQL instructions for coding problems
        sql_instructions_for_coding = ""
        if sql_available:
            sql_instructions_for_coding = f"""
**🗄️ CONDITIONAL SQL ANALYSIS (for coding problems):** If the coding problem involves database interaction:
- Document any relevant table structures if deducible.
- Note relationships and foreign keys if apparent.
- Provide SQL query solutions or snippets as part of the coding solution if appropriate.
- If the problem IS an SQL problem, ensure solutions are in SQL.

Example SQL solution snippet format (if applicable within a broader coding solution):
```sql
-- SQL approach: [Brief description]
SELECT ... FROM ... WHERE ...;
```
---
"""

        # The prompt structure
        return f"""You are an expert AI assistant. Your task is to analyze the content of the provided screenshots.

**Overall Goal:** Provide a clear, accurate, and comprehensive analysis based on the dominant type of content in the screenshots.

**Content Assessment:**
First, carefully assess the screenshots to determine the primary type of information presented. This could be:
1.  **Multiple Choice Questions (MCQs):** Questions with several options, covering any topic (e.g., programming, aptitude, cloud technologies like AWS/GCP, quantitative, general knowledge).
2.  **Coding Problem:** A specific programming challenge requiring algorithmic thinking, code implementation, and analysis.
3.  **Mixed Content:** A combination of MCQs and coding problems, or other informational content.
4.  **Other:** If the content doesn't fit the above, describe it and assist as best as you can.

{language_context}
---

**SECTION 1: MULTIPLE CHOICE QUESTION (MCQ) ANALYSIS**
*If MCQs are present (either exclusively or as part of mixed content), use this section.*

**Instructions for MCQs:**
- This applies to MCQs on **any subject**.
- If there are multiple MCQs, address **each one individually and systematically**.\n
For EACH MCQ identified:
1.  **Question Number/Identifier:** (e.g., Q1, Question 5, or a brief unique part of the question if unnumbered)
2.  **Question Text:** Clearly restate or summarize the question.
3.  **Options:** List all provided options (e.g., A. Option 1, B. Option 2, C. Option 3, D. Option 4).
4.  **Explanation:** Provide a clear and concise justification. Analyze each option as needed. Explain why the identified correct option is indeed correct, and if helpful, why other key options are incorrect. Your reasoning should clearly lead to the answer.
5.  **Correct Answer:** After providing the explanation, clearly state the correct option (e.g., "Based on the explanation, the correct answer is C. Option 3").\n
---

**SECTION 2: CODING PROBLEM ANALYSIS & SOLUTION**
*If a coding problem is present (either exclusively or as part of mixed content), use this section. This can also apply if MCQs are about specific coding concepts that require a detailed algorithmic explanation.*

{sql_instructions_for_coding if sql_available else "<!-- No specific SQL instructions for coding problem as SQL was not indicated as a relevant language. -->"}

**I. 🎯 PROBLEM ANALYSIS (for the coding problem)**

A.  **Problem Understanding:**
    -   **Problem Statement:** Consolidate information from ALL screenshots to give a clear restatement of the coding problem.
    -   **Input/Output:** Specify the expected input format, output format, and provide examples if available.
    -   **Constraints & Edge Cases:** List key limitations, constraints (e.g., time/space complexity), and important edge cases to consider.
    -   **Core Challenge:** Identify the main algorithmic or conceptual difficulty of the problem.

**II. 🚀 SOLUTION APPROACHES (for the coding problem)**
*Provide at least two well-explained approaches. Focus on clarity, correctness, and interview-readiness. Use {primary_language} for code examples unless the problem specifies otherwise.*\\n\nA.  **Approach 1: [RECOMMENDED/OPTIMAL SOLUTION]**
    1.  **Algorithm/Technique & Initial Intuition:** Identify the core algorithm/technique (e.g., "Two Pointers", "BFS", "Dynamic Programming"). Explain the initial intuition or key insight that suggests this approach is suitable for the problem based on its characteristics (e.g., sorted input, graph traversal, overlapping subproblems).
    2.  **Complexity Analysis:**
        -   Time Complexity: O(?) (Explain reasoning)
        -   Space Complexity: O(?) (Explain reasoning)
    3.  **Code Implementation ({primary_language}):**
        ```{(primary_language).lower()}
// Approach 1: [Brief description of this specific implementation, highlighting key logic] [RECOMMENDED/OPTIMAL SOLUTION]
// Time: O(?), Space: O(?)

// [Complete, production-ready code with clear comments and explanations for the coding problem]
// [Ensure the code is directly usable and well-formatted]
        ```
    4.  **Detailed Walkthrough / Dry Run:** Provide a detailed step-by-step walkthrough (dry run) of your code with a concrete example. Explain how the variables change and how the logic progresses to reach the solution for that example. Clearly show the state at each important step.
    5.  **Justification for Choice & Optimality:** Elaborate on why this specific algorithm/technique was chosen as the recommended solution. Discuss its advantages (e.g., optimality in time/space for the given constraints, clarity, common patterns for this problem type) compared to other potential naive or less optimal approaches.\\n\nB.  **Approach 2: [ALTERNATIVE SOLUTION] (Optional, if relevant)**
    1.  **Algorithm/Technique & Initial Intuition:** Identify the alternative algorithm/technique. Explain the intuition or reason for considering this alternative.
    2.  **Complexity Analysis:**
        -   Time Complexity: O(?) (Explain reasoning)
        -   Space Complexity: O(?) (Explain reasoning)
    3.  **Code Implementation ({primary_language}):**
        ```{(primary_language).lower()}
// Approach 2: [Brief description of this specific implementation, highlighting key logic]  
// Time: O(?), Space: O(?)

// [Alternative implementation with comments for the coding problem]
        ```
    4.  **Detailed Walkthrough / Dry Run:** Provide a detailed step-by-step walkthrough (dry run) of your alternative code with a concrete example. Explain how the variables change and how the logic progresses.
    5.  **Trade-offs & When to Use:** Compare this approach with Approach 1 (e.g., "Simpler to implement but less efficient for large inputs", "Better space complexity under certain conditions", "Useful if constraints were different"). Explain when this alternative might be preferred or is worth discussing.\\n\n**III. 📊 COMPARISON & INTERVIEW STRATEGY (for coding problems)**

| Aspect         | Approach 1        | Approach 2 (if provided) |
|----------------|-------------------|--------------------------|
| **Time**       | O(?)              | O(?)                     |
| **Space**      | O(?)              | O(?)                     |
| **Implementation Complexity** | [e.g., Simple/Medium/Complex] | [e.g., Simple/Medium/Complex] |

**Interview Recommendation:**
- Which approach to present first in an interview and why.
- When to discuss the alternative approach.

**Potential Follow-up Questions from Interviewer:**
- List 2-3 likely follow-up questions an interviewer might ask about your solution(s) and brief points for how to answer them.

---

**Final Instructions:**
- Be concise yet thorough.
- Ensure your analysis directly addresses the content of the screenshots.
- If providing code, make sure it is well-commented and follows best practices for {primary_language}.
"""

    async def get_all_vision_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all vision providers"""
        status = {}
        
        for manager_key, manager in self.vision_managers.items():
            try:
                # Perform health check
                is_healthy = await manager.health_check()
                status[manager_key] = manager.get_status()
                status[manager_key]["health_check_result"] = is_healthy
            except Exception as e:
                status[manager_key] = {
                    "provider": manager.provider_name,
                    "model": manager.model_name,
                    "is_healthy": False,
                    "error": str(e),
                    "health_check_result": False
                }
        
        return status

# Global vision service instance
vision_service = VisionService()

# Verification function
async def verify_vision_provider_connection(base_url: str, api_key: str, model_name: str, request_params: Optional[Dict[str, Any]] = None) -> bool:
    """Verify a vision provider connection - simplified to avoid complex vision tests"""
    try:
        temp_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        
        # Just test basic connectivity with models.list() - don't do complex vision tests
        await asyncio.wait_for(temp_client.models.list(), timeout=20.0)
        
        # For OpenRouter, note that we have provider routing but skip complex testing
        if request_params and "provider" in request_params:
            print(f"INFO: OpenRouter vision model {model_name} configured with provider routing: {request_params}")
            print(f"INFO: Skipping complex vision test - basic connectivity verified")
        
        print(f"✅ Vision connection to {base_url} with model {model_name} is valid.")
        return True
    except asyncio.TimeoutError:
        print(f"⏱️ TIMEOUT: Vision connection to {base_url} timed out")
        return False
    except APIStatusError as e:
        print(f"❌ ERROR: Vision API key verification failed for {base_url}. Status: {e.status_code}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Vision provider verification error for {base_url}: {e}")
        return False