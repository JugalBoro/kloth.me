"""
Service for LLM-based query planning and response generation using Google Gemini.
"""

from google import genai
from google.genai import types
from typing import List, Optional
import json

from app.config import get_settings
from app.models import QueryPlan


class LLMPlanner:
    """Service for LLM-based query planning and response generation using Gemini."""
    
    def __init__(self):
        """Initialize Gemini client."""
        settings = get_settings()
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model_name = settings.gemini_model
    
    async def create_query_plan(
        self,
        user_message: str,
        image: Optional[object] = None,  # PIL Image
        chat_history: Optional[List[dict]] = None
    ) -> QueryPlan:
        """
        Generate a structured query plan using LLM.
        
        Args:
            user_message: User's text query
            image: PIL Image object (if uploaded)
            chat_history: Previous chat messages for context
            
        Returns:
            QueryPlan with refined queries and search strategy
        """
        system_prompt = """You are a smart fashion search planner. Your goal is to return a search plan JSON.

CRITICAL: First, analyze the image (if provided). 
1. Is it fashion-related (clothing, shoes, accessories, jewelry)?
2. If the image is NOT fashion-related (e.g., a car, landscape, animal, document):
   - Set "use_image": false
   - If user text IS present and specific (e.g. "blue shirts"), generate refined queries based on TEXT ONLY.
   - If user text is empty/generic, set "refined_queries": [].
   - Set "reasoning": "Image contains [X] which is not fashion-related. Ignoring image and using text query."

If the image IS fashion-related:
   - Set "use_image": true
   - Extract visual attributes for filters/refined queries.

Output JSON structure:
1. refined_queries: List[str] - text queries to run
2. use_image: bool - whether to search by image embedding
3. text_weight: float 0-1
4. top_k: int
5. filters: dict or null
6. reasoning: str

Examples:
- Image: [Red Car], Text: "" -> {"refined_queries": [], "use_image": false, "reasoning": "Image of car ignored."}
- Image: [House], Text: "find me blue color shirts" -> {"refined_queries": ["blue color shirts", "blue shirts"], "use_image": false, "text_weight": 1.0, "reasoning": "Image is a house (irrelevant). Using user text query only."}
- Image: [Blue Dress], Text: "matches for this" -> {"refined_queries": ["blue dress"], "use_image": true, "reasoning": "Fashion image detected."}
"""

        # Build prompt content
        contents = [system_prompt, "\n\n"]
        
        # Add chat history
        if chat_history:
            history_str = "Previous conversation:\n"
            for msg in chat_history[-3:]:
                history_str += f"{msg['role']}: {msg['content']}\n"
            contents.append(history_str + "\n")
        
        # Add current query
        query_str = f"User Query: \"{user_message}\"\n"
        if image:
            query_str += "[User uploaded an image]"
            contents.append(query_str)
            contents.append(image) # Pass the actual PIL image to Gemini
        else:
            contents.append(query_str)
        
        try:
            # Generate with Gemini
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=500,
                    response_mime_type="application/json" # Enforce strict JSON
                )
            )
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            plan_json = json.loads(response_text)
            return QueryPlan(**plan_json)
            
        except Exception as e:
            print(f"Error creating query plan: {e}")
            # Fallback plan
            # Fallback plan
            has_image = image is not None
            return QueryPlan(
                refined_queries=[user_message],
                use_image=has_image,
                text_weight=0.5 if has_image else 1.0,
                top_k=20,
                reasoning="Fallback plan due to LLM error"
            )
    
    async def generate_response(
        self,
        user_query: str,
        products: List[dict],
        query_plan: Optional[QueryPlan] = None
    ) -> str:
        """
        Generate a natural language response summarizing search results.
        
        Args:
            user_query: Original user query
            products: List of product results (with description, score)
            query_plan: Optional query plan for context
            
        Returns:
            Natural language summary
        """
        if not products:
            if query_plan and not query_plan.use_image and query_plan.reasoning:
                return f"I couldn't find any products. {query_plan.reasoning}"
            return "I couldn't find any products matching your query. Please try a different search."
        
        # Prepare product summaries (top 5 only)
        product_summaries = []
        for i, p in enumerate(products[:5], 1):
            product_summaries.append(
                f"{i}. {p['description'][:100]}... (relevance: {p['score']:.2f})"
            )
        
        products_text = "\n".join(product_summaries)
        
        # Extract planner context
        planner_context = ""
        if query_plan:
            planner_context = f"Planner Reasoning: {query_plan.reasoning}\nImage Used: {query_plan.use_image}"
        
        prompt = f"""You are a helpful fashion shopping assistant. Given search results, write a 2-3 sentence summary in a Perplexity-style response.

Guidelines:
- Be concise, engaging, and helpful (max 3 sentences)
- Highlight the diversity of styles, colors, and key features found
- Mention the total number of results found in a natural way
- Adopt a "Perplexity-style" direct answer tone
- Do NOT list individual products or use bullet points
- Focus on giving a high-level overview of the collection found

CRITICAL TRANSPARENCY:
- Read the "Planner Reasoning".
- If the reasoning says the user added an image but it was IGNORED (e.g. unrelated, not fashion), you MUST mention this.
- Example: "I noticed the image you uploaded appears to be a [object], which isn't fashion-related, so I focused on your request for [text query]."

User query: "{user_query}"

{planner_context}

Top results:
{products_text}

Total results: {len(products)}

Write a brief summary of what was found, including any transparency notes about the image:"""

        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=200,
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return f"I found {len(products)} products matching your query. Check out the results below!"


def get_llm_planner() -> LLMPlanner:
    """Get LLM planner instance."""
    return LLMPlanner()
