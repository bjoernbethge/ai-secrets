#!/usr/bin/env python3
"""
Pydantic AI Example: AI Agent with Secret Management and Tool Approval

This example demonstrates:
1. Using ai-secrets to securely manage API keys for an AI agent
2. Human-in-the-loop tool approval for sensitive operations
3. Structured output with Pydantic models
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext

# Import our ai-secrets storage
from ai_secrets.storage import SecretsStore


@dataclass
class AgentDependencies:
    """Dependencies injected into the agent context."""
    
    secrets_store: SecretsStore
    user_id: str
    max_cost_usd: float = 10.0  # Maximum allowed API cost


class APICallResult(BaseModel):
    """Structured output for API operations."""
    
    service: str = Field(description="Service name (e.g., 'openai', 'anthropic')")
    operation: str = Field(description="Operation performed")
    success: bool = Field(description="Whether operation succeeded")
    message: str = Field(description="Human-readable result message")
    cost_estimate_usd: float = Field(description="Estimated cost in USD", ge=0)
    requires_approval: bool = Field(description="Whether this required approval")


def create_agent() -> Agent[AgentDependencies, APICallResult]:
    """
    Create and configure the AI agent with tools.
    
    This is a factory function to avoid initializing the agent at module import time,
    which would require the OPENAI_API_KEY to be set even if just importing the module.
    """
    # Create agent with structured output
    api_agent = Agent(
        "openai:gpt-4o-mini",  # Using cheaper model for demo
        deps_type=AgentDependencies,
        output_type=APICallResult,
        system_prompt=(
            "You are an API orchestration agent that helps users make API calls to various services. "
            "Always check if API keys are available before attempting operations. "
            "Be transparent about costs and always ask for approval for expensive operations."
        ),
    )

    @api_agent.system_prompt
    async def add_user_context(ctx: RunContext[AgentDependencies]) -> str:
        """Add user-specific context to system prompt."""
        return (
            f"The user ID is '{ctx.deps.user_id}'. "
            f"Maximum allowed cost per operation: ${ctx.deps.max_cost_usd:.2f}"
        )

    @api_agent.tool
    async def check_api_key(
        ctx: RunContext[AgentDependencies],
        service_name: str,
    ) -> dict[str, bool | str]:
        """
        Check if an API key exists for a service.
        
        Args:
            ctx: Runtime context with secrets store
            service_name: Name of the service (e.g., 'OPENAI_API_KEY', 'HF_TOKEN')
        
        Returns:
            Dictionary with 'exists' status and optional 'message'
        """
        store = ctx.deps.secrets_store
        exists = store.get(service_name) is not None
        
        return {
            "exists": exists,
            "message": f"API key for {service_name} {'is available' if exists else 'not found'}"
        }

    @api_agent.tool(retries=2)
    async def get_api_key(
        ctx: RunContext[AgentDependencies],
        service_name: str,
    ) -> str:
        """
        Retrieve an API key from secure storage.
        
        This tool is automatically retried up to 2 times on failure.
        
        Args:
            ctx: Runtime context with secrets store
            service_name: Name of the service API key
        
        Returns:
            The API key value
            
        Raises:
            ModelRetry: If key not found (triggers retry or final error)
        """
        store = ctx.deps.secrets_store
        api_key = store.get(service_name)
        
        if not api_key:
            raise ModelRetry(
                f"API key '{service_name}' not found. "
                f"Please set it using: ai-secrets set {service_name} YOUR_KEY"
            )
        
        return api_key

    @api_agent.tool
    async def call_expensive_api(
        ctx: RunContext[AgentDependencies],
        service_name: str,
        operation: str,
        estimated_cost: float,
    ) -> dict[str, str | float | bool]:
        """
        Make an expensive API call that requires approval.
        
        This is a mock function demonstrating tool approval for cost-sensitive operations.
        In a real application, this would make actual API calls.
        
        Args:
            ctx: Runtime context
            service_name: API service to call (e.g., 'openai', 'anthropic')
            operation: Description of operation (e.g., 'Generate 10k tokens')
            estimated_cost: Estimated cost in USD
        
        Returns:
            Dictionary with operation result
        """
        # Check cost threshold
        if estimated_cost > ctx.deps.max_cost_usd:
            return {
                "success": False,
                "message": f"Cost ${estimated_cost:.2f} exceeds maximum allowed ${ctx.deps.max_cost_usd:.2f}",
                "requires_approval": True,
            }
        
        # In a real app, you would:
        # 1. Get API key using get_api_key()
        # 2. Make actual API call
        # 3. Return real results
        
        return {
            "success": True,
            "message": f"Successfully executed {operation} on {service_name}",
            "cost": estimated_cost,
            "requires_approval": estimated_cost > 5.0,
        }
    
    return api_agent


async def main():
    """Example usage with tool approval workflow."""
    print("🤖 Pydantic AI + ai-secrets Example\n")
    
    # Initialize secrets store for this agent
    # In production, use a unique service name per environment
    store = SecretsStore(service_name="demo-ai-agent")
    
    # Ensure we have required API keys (for demo purposes)
    if not store.get("OPENAI_API_KEY"):
        print("⚠️  Setting up demo API key...")
        store.set("OPENAI_API_KEY", "sk-demo-key-12345")
        print("✓ Demo OPENAI_API_KEY stored\n")
    
    # Create the agent
    api_agent = create_agent()
    
    # Create dependencies
    deps = AgentDependencies(
        secrets_store=store,
        user_id="user123",
        max_cost_usd=8.0,
    )
    
    # Example 1: Check if API key exists
    print("📋 Example 1: Check API key availability")
    result = await api_agent.run(
        "Check if we have an OpenAI API key available",
        deps=deps
    )
    print(f"Result: {result.output}\n")
    
    # Example 2: Low-cost operation (no approval needed)
    print("📋 Example 2: Low-cost operation (auto-approved)")
    result = await api_agent.run(
        "Make a small API call to OpenAI, estimated cost $2",
        deps=deps
    )
    print(f"Result: {result.output}\n")
    
    # Example 3: High-cost operation (requires approval)
    print("📋 Example 3: High-cost operation (requires approval)")
    result = await api_agent.run(
        "I need to process a large batch that will cost about $6",
        deps=deps
    )
    print(f"Result: {result.output}\n")
    
    # Example 4: Over budget (should be rejected)
    print("📋 Example 4: Over-budget operation (rejected)")
    result = await api_agent.run(
        "Process something that costs $15",
        deps=deps
    )
    print(f"Result: {result.output}\n")
    
    # Cleanup demo data
    print("🧹 Cleaning up demo secrets...")
    store.delete("OPENAI_API_KEY")
    print("✓ Demo complete!")


if __name__ == "__main__":
    import asyncio
    
    # Run the example
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

