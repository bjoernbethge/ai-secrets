# ai-secrets Examples

This directory contains practical examples demonstrating how to use `ai-secrets` in real-world scenarios.

## 📁 Examples

### 🤖 Pydantic AI Example (`pydantic_ai_example.py`)

Demonstrates integration with [Pydantic AI](https://ai.pydantic.dev/) for building AI agents with secure secret management.

**Features shown:**
- ✅ Secure API key management for AI agents
- ✅ Tool approval workflow for cost-sensitive operations
- ✅ Structured outputs with Pydantic models
- ✅ Dependency injection with agent context
- ✅ Automatic retries for tool failures
- ✅ Budget controls and cost thresholds

**Install dependencies:**
```bash
# Install ai-secrets with Pydantic AI support
uv pip install ai-secrets "pydantic-ai[openai]"

# Or add to your project
uv add ai-secrets "pydantic-ai[openai]"
```

**Run the example:**
```bash
# Set your OpenAI API key first (for real usage)
export OPENAI_API_KEY="sk-your-actual-key"

# Run the example
python examples/pydantic_ai_example.py
```

**What the example demonstrates:**

1. **Secret Management for AI Agents**
   - Stores API keys securely in OS keyring
   - Checks key availability before operations
   - Retrieves keys only when needed

2. **Tool Approval Workflow**
   - Low-cost operations: auto-approved
   - High-cost operations: requires approval
   - Over-budget operations: automatically rejected

3. **Structured Agent Design**
   - Type-safe dependencies with `AgentDependencies`
   - Structured outputs with Pydantic models
   - Clear separation of concerns

4. **Error Handling**
   - Automatic retries for transient failures
   - Clear error messages with remediation steps
   - Graceful degradation

## 🔐 Best Practices

### 1. Use Service-Specific Namespaces

```python
# Development
dev_store = SecretsStore(service_name="myapp-dev")

# Production
prod_store = SecretsStore(service_name="myapp-prod")

# Per-agent isolation
agent_store = SecretsStore(service_name="ai-agent-claude")
```

### 2. Implement Cost Controls

```python
@dataclass
class AgentDependencies:
    secrets_store: SecretsStore
    max_cost_usd: float = 10.0
    daily_budget_usd: float = 100.0
```

### 3. Use Tool Approval for Sensitive Operations

```python
@agent.tool(retries=2)
async def sensitive_operation(ctx: RunContext[Deps]) -> dict:
    """Operation requiring approval."""
    if ctx.deps.cost > ctx.deps.max_cost:
        raise ModelRetry("Cost exceeds budget - requires approval")
    # ... perform operation
```

### 4. Never Log or Print Secrets

```python
# ❌ BAD
print(f"Using API key: {api_key}")
logger.info(f"Key: {store.get('KEY')}")

# ✅ GOOD
logger.info("API key retrieved successfully")
print("✓ Authentication configured")
```

## 🚀 More Examples Coming Soon

- **LangChain Integration**: Using ai-secrets with LangChain agents
- **Multi-Provider Routing**: Switching between OpenAI/Anthropic/etc.
- **Secret Rotation**: Automatic key rotation workflows
- **Team Collaboration**: Shared secrets with role-based access

## 📚 Related Documentation

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [ai-secrets README](../README.md)
- [Tool Approval Guide](https://ai.pydantic.dev/tools/#tool-approval)

## 🤝 Contributing Examples

Have a cool use case? We'd love to see it! 

1. Create a new `.py` file in `examples/`
2. Add clear comments and docstrings
3. Update this README
4. Submit a PR

**Example ideas:**
- CI/CD integration (GitHub Actions, GitLab CI)
- Cloud provider integration (AWS, GCP, Azure)
- Database connection management
- Multi-tenant applications
- Secret sharing workflows

