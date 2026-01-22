# Claude API Setup Guide

Complete guide for configuring the proactive AI assistant to use Anthropic's Claude API for production-quality conversational AI.

## Table of Contents

- [Quick Setup](#quick-setup)
- [Model Selection](#model-selection)
- [Configuration Reference](#configuration-reference)
- [Cost Estimation](#cost-estimation)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

## Quick Setup

### Step 1: Get an API Key

1. Visit [console.anthropic.com](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to **API Keys** section
4. Click **Create Key**
5. Copy your API key (starts with `sk-ant-...`)

> **Note**: Keep your API key secure. Never commit it to version control.

### Step 2: Configure Your Environment

```bash
cd backend

# Copy the example environment file
cp .env.example .env

# Edit .env with your preferred editor
nano .env  # or vim, code, etc.
```

Add your API key to `.env`:

```bash
# Switch to Claude API
CHAT_PROVIDER=claude

# Paste your API key here
CLAUDE_API_KEY=sk-ant-your-actual-api-key-here

# Choose a model (Haiku is cheapest for dev)
CLAUDE_MODEL=claude-haiku-4-5-20251001
```

### Step 3: Install and Run

```bash
# Install dependencies (includes anthropic package)
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Step 4: Verify

You should see this message when the server starts:

```
Using Claude API with model: claude-haiku-4-5-20251001
```

**That's it!** Your assistant now uses real Claude AI. Test it by opening the frontend.

## Model Selection

Choose the right model for your needs:

| Model | Speed | Quality | Input/Output Cost* | Best For |
|-------|-------|---------|-------------------|----------|
| **Haiku 4.5** | ⚡⚡⚡ | ⭐⭐⭐ | $1.00 / $5.00 | **Development & Testing** |
| **Haiku 3.5** | ⚡⚡⚡ | ⭐⭐ | $0.80 / $4.00 | Budget-conscious dev |
| **Sonnet 3.7** | ⚡⚡ | ⭐⭐⭐ | $3.00 / $15.00 | Balanced production |
| **Sonnet 4.5** | ⚡⚡ | ⭐⭐⭐⭐ | $3.00 / $15.00 | High-quality apps |
| **Opus 4.5** | ⚡ | ⭐⭐⭐⭐⭐ | $15.00 / $75.00 | Premium experiences |

\* *Cost per million tokens (USD)*

### Model IDs

```bash
# Haiku 4.5 - Fastest and most capable Haiku (recommended for dev)
CLAUDE_MODEL=claude-haiku-4-5-20251001

# Haiku 3.5 - Previous Haiku version
CLAUDE_MODEL=claude-haiku-4-5-20251001

# Sonnet 3.7 - Balanced performance
CLAUDE_MODEL=claude-sonnet-3-7-20250219

# Sonnet 4.5 - Most capable Sonnet
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# Opus 4.5 - Most powerful
CLAUDE_MODEL=claude-opus-4-5-20251101
```

**Pro tip**: Start with Haiku 4.5 for development, upgrade to Sonnet for production.

## Configuration Reference

All settings go in `backend/.env`:

```bash
# ============================================
# REQUIRED: Provider Selection
# ============================================
CHAT_PROVIDER=claude              # "mock" or "claude"

# ============================================
# REQUIRED (when using Claude): API Key
# ============================================
CLAUDE_API_KEY=sk-ant-...         # Get from console.anthropic.com

# ============================================
# OPTIONAL: Model Selection
# ============================================
CLAUDE_MODEL=claude-haiku-4-5-20251001  # Default if not specified

# ============================================
# OPTIONAL: Generation Parameters
# ============================================
MAX_TOKENS=1024                   # Response length (1-4096)
TEMPERATURE=0.7                   # Creativity (0.0-1.0)
```

### Parameter Guide

**MAX_TOKENS**
- Controls maximum response length
- Range: 1-4096
- Default: 1024 (good for most conversations)
- Higher values allow longer responses but cost more

**TEMPERATURE**
- Controls randomness/creativity
- Range: 0.0-1.0
- Recommended values:
  - `0.0-0.3`: Focused, deterministic (factual Q&A)
  - `0.4-0.7`: Balanced, natural (recommended)
  - `0.8-1.0`: Creative, varied (brainstorming)

## Cost Estimation

### Development/Testing (Haiku)

**Typical message:**
- Input: ~200 tokens
- Output: ~300 tokens
- Cost: ~$0.001 (one-tenth of a cent)

**1,000 test messages:** ~$1.00

### Production (Sonnet)

**Typical conversation:**
- 10 messages per session
- ~2,000 input + ~3,000 output tokens per session
- Cost: ~$0.05 (5 cents) per session

**Scale estimate:**
- 1,000 users/day: ~$50/day = ~$1,500/month
- 10,000 users/day: ~$500/day = ~$15,000/month

**Cost optimization tips:**
1. Start with Haiku - it's surprisingly capable for most use cases
2. Use lower MAX_TOKENS for shorter conversations
3. Monitor usage in the Anthropic console
4. Set billing alerts to avoid surprises

## Troubleshooting

### Error: "CLAUDE_API_KEY must be set when CHAT_PROVIDER=claude"

**Cause:** You set `CHAT_PROVIDER=claude` without providing an API key.

**Fix:**
```bash
# Edit your .env file and add:
CLAUDE_API_KEY=sk-ant-your-actual-key
```

### Error: "anthropic package not installed"

**Cause:** The Anthropic SDK is missing.

**Fix:**
```bash
pip install -r requirements.txt
# or directly:
pip install anthropic
```

### Error: "Invalid API key"

**Cause:** API key is incorrect, expired, or has wrong permissions.

**Fix:**
1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Generate a new API key
3. Update `.env` with the new key
4. Restart the server

### Responses are slow

**Cause:** Using a more powerful but slower model (Opus).

**Fix:** Switch to Haiku for faster responses:
```bash
CLAUDE_MODEL=claude-haiku-4-5-20251001
```

### Want to switch back to mock mode

**Fix:** Change `.env`:
```bash
CHAT_PROVIDER=mock
```

Or delete the `.env` file entirely (mock is the default).

## Advanced Topics

### Security Best Practices

1. **Never commit `.env`**
   - Already excluded in `.gitignore`
   - Use `.env.example` for templates

2. **Rotate keys regularly**
   - Generate new keys periodically
   - Delete old keys after rotation

3. **Use environment-specific keys**
   - Different keys for dev/staging/prod
   - Apply least-privilege principle

4. **Monitor usage**
   - Check [console.anthropic.com](https://console.anthropic.com/) regularly
   - Set up billing alerts

### File Structure

After setup, your backend should look like:

```
backend/
├── .env                    # Your API key (NEVER commit!)
├── .env.example           # Template (safe to commit)
├── requirements.txt
├── app/
│   ├── config.py          # Reads .env configuration
│   ├── chat_provider.py   # Provider abstraction
│   ├── conversation.py    # Uses providers
│   └── ...
```

### Custom Provider Implementation

Want to add OpenAI, Gemini, or local models?

1. Implement the `ChatProvider` interface in `app/chat_provider.py`:

```python
from app.chat_provider import ChatProvider, ChatMessage, ChatResponse

class MyCustomProvider(ChatProvider):
    def generate_response(
        self,
        messages: list[ChatMessage],
        system_prompt: str = None,
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> ChatResponse:
        # Your implementation here
        # Call your LLM API
        response_text = "..."

        return ChatResponse(
            content=response_text,
            model="my-custom-model"
        )

    def get_model_name(self) -> str:
        return "my-custom-model"
```

2. Update `app/config.py` to support your provider:

```python
# Add new provider type
if config.chat_provider == "custom":
    from .my_custom_provider import MyCustomProvider
    provider = MyCustomProvider(...)
```

The rest of the system works automatically!

### Rate Limits

Claude API has rate limits based on your account tier:

- **Free tier**: Limited requests per minute
- **Paid tier**: Higher limits, see [console.anthropic.com](https://console.anthropic.com/)

**Handling rate limits:**
- The SDK automatically retries with exponential backoff
- Monitor your usage in the console
- Upgrade your tier if needed

### Testing the API Directly

Test your configuration with curl:

```bash
# Chat endpoint
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "Explain distributed consensus in simple terms"
  }'

# Should return a response from Claude!
```

## Resources

- **Claude API Documentation**: [docs.anthropic.com](https://docs.anthropic.com/)
- **API Console**: [console.anthropic.com](https://console.anthropic.com/)
- **Pricing**: [anthropic.com/pricing](https://www.anthropic.com/pricing)
- **Status Page**: [status.anthropic.com](https://status.anthropic.com/)

## Next Steps

1. ✅ Get API key from Anthropic console
2. ✅ Create `.env` file with your key
3. ✅ Install dependencies
4. ✅ Start server and verify Claude is active
5. ✅ Test with the frontend
6. ✅ Monitor usage in console
7. ✅ Optimize model choice based on needs

Happy building! 🚀
