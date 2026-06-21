from strands_sdk.agent import StrandsAgent
from strands_sdk.llm import BedrockModel

def get_alternative_discovery_agent():
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")
    
    def web_search(query: str):
        # Implement web search using duckduckgo or similar
        return [{"title": "GreenSeating India", "snippet": "Leading manufacturer of sustainable office chairs in India."}]
    
    agent = StrandsAgent(
        name="Alternative Discovery Agent",
        role="Discover potential alternative suppliers using external sources (Amazon Business, IndiaMART, GeM, Alibaba, Web). Analyze risk, sustainability, and cost to recommend the best option.",
        model=model,
        tools=[web_search]
    )
    return agent
