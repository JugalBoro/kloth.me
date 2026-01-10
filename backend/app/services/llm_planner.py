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
        has_image: bool = False,
        chat_history: Optional[List[dict]] = None
    ) -> QueryPlan:
        """
        Generate a structured query plan using LLM.
        
        Args:
            user_message: User's text query
            has_image: Whether an image was uploaded
            chat_history: Previous chat messages for context
            
        Returns:
            QueryPlan with refined queries and search strategy
        """
        system_prompt = """You are a fashion search query planner. Your job is to analyze user queries and create an optimal search plan.

Given a user's message and whether they uploaded an image, you must output a JSON object with:
1. refined_queries: Array of 1-3 text queries to search (decompose complex queries, add synonyms)
2. use_image: Boolean - whether to use image-based search
3. text_weight: Float 0-1 - how much to weight text vs image results (0.5 = equal, 1.0 = text only)
4. top_k: Integer 10-50 - how many results to retrieve per modality
5. filters: Optional dictionary of strict attribute filters. Keys: "color", "category". Extract ONLY if explicitly mentioned.
6. reasoning: Brief explanation of your strategy

Examples:

Query: "black midi dress for a summer wedding"
{
  "refined_queries": ["black midi dress", "summer wedding dress", "elegant black dress"],
  "use_image": false,
  "text_weight": 1.0,
  "top_k": 20,
  "filters": {"color": "black", "category": "dress"},
  "reasoning": "User specified color 'black', apply strict filter."
}

Query: "same style but in red" [with image]
{
  "refined_queries": ["red dress", "red clothing"],
  "use_image": true,
  "text_weight": 0.3,
  "top_k": 20,
  "filters": {"color": "red"},
  "reasoning": "User wants image-based search with color modification."
}

Query: "casual summer outfit" [with image]
{
  "refined_queries": ["casual summer outfit", "lightweight summer clothing"],
  "use_image": true,
  "text_weight": 0.5,
  "top_k": 25,
  "filters": null,
  "reasoning": "No specific color or category constraints."
}

Output ONLY valid JSON, no additional text."""

        # Build prompt with context
        prompt_parts = [system_prompt, "\n\n"]
        
        # Add chat history if available
        if chat_history:
            prompt_parts.append("Previous conversation:\n")
            for msg in chat_history[-3:]:  # Last 3 messages
                prompt_parts.append(f"{msg['role']}: {msg['content']}\n")
            prompt_parts.append("\n")
        
        # Add current query
        user_content = f"Query: \"{user_message}\""
        if has_image:
            user_content += " [with image]"
        prompt_parts.append(user_content)
        
        full_prompt = "".join(prompt_parts)
        
        
        try:
            # Generate with Gemini
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=500,
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
            return "I couldn't find any products matching your query. Please try a different search."
        
        # Prepare product summaries (top 5 only)
        product_summaries = []
        for i, p in enumerate(products[:5], 1):
            product_summaries.append(
                f"{i}. {p['description'][:100]}... (relevance: {p['score']:.2f})"
            )
        
        products_text = "\n".join(product_summaries)
        
        prompt = f"""You are a helpful fashion shopping assistant. Given search results, write a 2-3 sentence summary in a Perplexity-style response.

Guidelines:
- Be concise, engaging, and helpful (max 3 sentences)
- Highlight the diversity of styles, colors, and key features found
- Mention the total number of results found in a natural way
- Adopt a "Perplexity-style" direct answer tone
- Do NOT list individual products or use bullet points
- Focus on giving a high-level overview of the collection found

User query: "{user_query}"

Top results:
{products_text}

Total results: {len(products)}

Write a brief summary of what was found:"""

        
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
