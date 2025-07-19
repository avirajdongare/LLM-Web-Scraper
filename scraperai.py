import os
import json
import asyncio
from dotenv import load_dotenv
from bs4 import BeautifulSoup

from mcp.server.fastmcp import FastMCP
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy

# Load environment variables
load_dotenv()

# Load API tokens
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# For future fallback support

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

print(f"[STARTUP] Gemini API Key detected: {bool(GEMINI_API_KEY)}")
# print(f"[STARTUP] OpenAI API Key detected: {bool(OPENAI_API_KEY and OPENAI_API_KEY.strip())}")
# print(f"[STARTUP] Mistral API Key detected: {bool(MISTRAL_API_KEY and MISTRAL_API_KEY.strip())}")

# Initialize the MCP server
agent = FastMCP("webcrawl")
agent.settings.port = 8002

@agent.tool()
async def scrape_url(target_url: str) -> str:
    """
    Retrieve a webpage's content and return its markdown representation.
    """
    try:
        async with AsyncWebCrawler() as crawler:
            response = await crawler.arun(url=target_url)
            return response.markdown.raw_markdown if response.markdown else "No content retrieved."
    except Exception as ex:
        return f"[ERROR] Failed to scrape: {str(ex)}"

@agent.tool()
async def extract_text_by_query(target_url: str, keyword: str, context: int = 300) -> str:
    """
    Search a webpage for a specific query and return relevant segments of text.
    """
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=target_url)
            if not result.markdown or not result.markdown.raw_markdown:
                return f"No readable content found on: {target_url}"

            text = result.markdown.raw_markdown
            keyword_lower = keyword.lower()
            content_lower = text.lower()

            indices = []
            pointer = 0

            while True:
                index = content_lower.find(keyword_lower, pointer)
                if index == -1:
                    break
                indices.append(index)
                pointer = index + len(keyword_lower)

            if not indices:
                return f"No instances of '{keyword}' were found."

            snippets = []
            for idx in indices[:5]:  # Limit to 5 results
                start = max(0, idx - context)
                end = min(len(text), idx + len(keyword_lower) + context)
                snippet = text[start:end]
                snippets.append(snippet)

            response = "\n\n---\n\n".join([f"Match {i+1}:\n{snip}" for i, snip in enumerate(snippets)])
            return f"Found {len(snippets)} relevant match(es):\n\n{response}"

    except Exception as ex:
        return f"[ERROR] Problem during query search: {str(ex)}"

@agent.tool()
async def smart_extract(target_url: str, instruction: str) -> str:
    """
    Use an LLM-powered extractor to pull structured data based on natural instructions.
    """
    try:
        if not GEMINI_API_KEY:
            return "Missing Gemini API key. Please define GOOGLE2_API_KEY or GOOGLE_API_KEY."

        print("[EXTRACTION] Gemini selected as the extraction engine.")

        # Define the strategy using Gemini
        strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider="gemini/gemini-2.0-flash",
                api_token=GEMINI_API_KEY
            ),
            extraction_type="natural",
            instruction=instruction,
            extra_args={"temperature": 0.2}
        )

        config = CrawlerRunConfig(extraction_strategy=strategy)

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=target_url, config=config)
            if not result.extracted_content:
                return f"No data extracted using instruction: '{instruction}'"

            output = result.extracted_content
            try:
                parsed = json.loads(output)
                output = json.dumps(parsed, indent=2)
            except Exception:
                pass

            return f"LLM Extraction Successful:\n\n{output}"

    except Exception as ex:
        return f"[ERROR] Smart extract failed: {str(ex)}"

# Run the server
if __name__ == "__main__":
    agent.run(transport="sse")
