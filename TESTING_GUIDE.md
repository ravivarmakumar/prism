# Testing Guide: A2A, AG-UI, and MCP Integration

## Quick Start Testing

### 1. Restart the Application
```bash
cd /Users/nishithmannuru/Documents/cursor/raviprism/prism
./venv/bin/streamlit run app.py
```

---

## Testing AG-UI (Agent UI)

### Step 1: Enable Agent Dashboard
1. **Start a PRISM Session**:
   - Fill out the sidebar form:
     - Student ID: `10005578` (or any ID)
     - Degree: Select any degree
     - Major: Enter any major (e.g., "Computer Science")
     - Course: Select a course
   - Click **"Start PRISM Session"**

2. **Enable Agent Dashboard**:
   - In the sidebar, check the box: **"🤖 Show Agent Dashboard"**
   - The dashboard will appear below the chat interface

### Step 2: Test Agent Flow Visualization
1. **Ask a Question**:
   - Type: `"What is machine learning?"` or any course-related question
   - Press Enter

2. **Observe Agent Dashboard**:
   - You should see a **flow diagram** showing:
     - ✅ Completed agents (green)
     - 🟢 Current active agent (dark green)
     - ⚪ Pending agents (gray)
   
3. **Check Agent Decisions**:
   - Look for metrics showing:
     - Is Relevant: ✅ Yes / ❌ No
     - Content Found: ✅ Yes / ❌ No
     - Is Vague: ⚠️ Yes / ✅ No
     - Evaluation: ✅ Passed / ⚠️ Failed

### Step 3: Test A2A Messages
1. **View A2A Messages**:
   - Scroll down in the agent dashboard
   - Look for section: **"📨 Agent-to-Agent Messages"**

2. **Verify Messages**:
   - You should see messages like:
     - `query_refinement → relevance: query_refined`
     - `relevance → course_rag: query_approved`
     - `course_rag → personalization: content_retrieved`
   
3. **Expand Message Details**:
   - Click on any message's "Message content" expander
   - Verify it shows relevant information

### Step 4: Test Multiple Questions
1. **Ask Multiple Questions**:
   - Ask 2-3 different questions
   - Each question should generate new A2A messages
   - Check that messages accumulate (shows last 10)

### ✅ AG-UI Confirmation Checklist
- [ ] Agent dashboard toggle appears in sidebar
- [ ] Dashboard shows when enabled
- [ ] Agent flow visualization displays correctly
- [ ] Current agent is highlighted (dark green)
- [ ] Completed agents show in green
- [ ] A2A messages section appears
- [ ] Messages show sender → receiver format
- [ ] Message content is expandable
- [ ] Agent decisions metrics display correctly

---

## Testing MCP Fallback

### Step 1: Verify Primary Method (OpenAI TTS)
1. **Generate a Podcast**:
   - Click the **➕** button next to the input field
   - Check **"🎙️ Generate Podcast"**
   - Select style: **Conversational**
   - Enter a topic: `"Neural Networks"` or any course topic
   - Press Enter

2. **Check Logs**:
   - Look at the terminal where Streamlit is running
   - You should see: `"Generating audio with OpenAI TTS API..."`
   - You should see: `"Audio combined successfully"`
   - **This confirms OpenAI TTS is working (primary method)**

### Step 2: Test MCP Fallback (Optional - Requires Node.js)
**Note**: MCP fallback only activates if OpenAI TTS fails. To test it:

1. **Simulate OpenAI TTS Failure** (for testing):
   - Temporarily modify `.env` to use an invalid OpenAI key
   - OR wait for a rate limit error
   - OR test when OpenAI API is down

2. **Check Fallback Activation**:
   - Look for log message: `"Attempting MCP fallback for audio generation..."`
   - Look for: `"MCP fallback succeeded"` or `"MCP fallback failed"`

3. **Verify MCP Requirements**:
   - MCP requires Node.js (already installed via nvm)
   - Check if Node.js is available:
     ```bash
     export NVM_DIR="$HOME/.nvm"
     [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
     node --version
     ```

### ✅ MCP Confirmation Checklist
- [ ] Podcast generation works with OpenAI TTS (primary)
- [ ] Logs show "Generating audio with OpenAI TTS API..."
- [ ] Audio file is created successfully
- [ ] If OpenAI TTS fails, MCP fallback is attempted
- [ ] MCP fallback logs appear (if activated)
- [ ] Application doesn't crash if MCP is unavailable

---

## Testing A2A Framework

### Step 1: Verify A2A Messages in State
1. **Ask a Question**:
   - Start a session and ask: `"Explain neural networks"`

2. **Check Terminal Logs**:
   - Look for A2A-related logs (if logging is enabled)
   - Messages are stored in state automatically

3. **View in Dashboard**:
   - Enable agent dashboard
   - Scroll to A2A messages section
   - Verify messages are being created

### Step 2: Test Message Types
Ask different types of questions to trigger different message types:

1. **Vague Question** (triggers `follow_up_needed`):
   - Ask: `"Tell me about it"`
   - Should see: `query_refinement → user: follow_up_needed`

2. **Irrelevant Question** (triggers `not_relevant`):
   - Ask: `"What's the weather today?"`
   - Should see: `relevance → user: not_relevant`

3. **Relevant Question** (triggers multiple messages):
   - Ask: `"What is machine learning?"`
   - Should see chain:
     - `query_refinement → relevance: query_refined`
     - `relevance → course_rag: query_approved`
     - `course_rag → personalization: content_retrieved`

### ✅ A2A Confirmation Checklist
- [ ] A2A messages appear in agent dashboard
- [ ] Messages show correct sender and receiver
- [ ] Message types are appropriate for the flow
- [ ] Messages accumulate (up to 10 shown)
- [ ] Message content is accessible
- [ ] No errors in console/logs related to A2A

---

## Comprehensive Test Scenario

### Full Workflow Test
1. **Start Application**: `./venv/bin/streamlit run app.py`

2. **Start Session**:
   - Fill sidebar form
   - Click "Start PRISM Session"

3. **Enable Agent Dashboard**:
   - Check "🤖 Show Agent Dashboard"

4. **Test Chat**:
   - Ask: `"What is machine learning?"`
   - **Verify**:
     - ✅ Response appears in chat
     - ✅ Agent dashboard shows flow
     - ✅ A2A messages appear
     - ✅ Agent decisions show metrics

5. **Test Podcast**:
   - Click ➕ button
   - Enable podcast generation
   - Enter topic: `"Neural Networks"`
   - **Verify**:
     - ✅ Script is generated
     - ✅ Audio is created
     - ✅ Audio player appears
     - ✅ No errors in logs

6. **Test Multiple Interactions**:
   - Ask 3-4 questions
   - **Verify**:
     - ✅ A2A messages accumulate
     - ✅ Agent flow updates
     - ✅ No performance issues

---

## Troubleshooting

### AG-UI Not Showing
- **Check**: Is "Show Agent Dashboard" checked in sidebar?
- **Check**: Is session active? (sidebar shows "✅ Session Active")
- **Check**: Are there any errors in browser console? (F12)

### A2A Messages Not Appearing
- **Check**: Terminal logs for A2A-related errors
- **Check**: Is the question triggering agent flow?
- **Check**: Try asking a clear, relevant question

### MCP Fallback Not Working
- **Check**: Is Node.js installed? (`node --version`)
- **Check**: Is MCP available? (check logs)
- **Note**: MCP only activates if OpenAI TTS fails

### Application Errors
- **Check**: Terminal output for Python errors
- **Check**: Browser console (F12) for JavaScript errors
- **Verify**: All dependencies installed (`pip install -r requirements.txt`)

---

## Expected Behavior Summary

### ✅ Normal Operation
- Application starts without errors
- Chat works as before
- Agent dashboard is optional (toggle)
- A2A messages are created automatically
- Podcast generation uses OpenAI TTS (primary)
- MCP fallback activates only on failure

### ✅ New Features Visible
- Agent dashboard toggle in sidebar
- Agent flow visualization
- A2A message viewer
- Agent decision metrics
- Enhanced logging (for debugging)

---

## Success Criteria

### All Tests Pass If:
1. ✅ Application runs without errors
2. ✅ Existing features work (chat, flashcards, podcasts)
3. ✅ Agent dashboard appears when enabled
4. ✅ A2A messages are visible in dashboard
5. ✅ Agent flow visualization works
6. ✅ Podcast generation works (OpenAI TTS)
7. ✅ No breaking changes to existing functionality

---

## Quick Test Commands

```bash
# 1. Start the app
cd /Users/nishithmannuru/Documents/cursor/raviprism/prism
./venv/bin/streamlit run app.py

# 2. In browser:
# - Go to http://localhost:8501
# - Fill sidebar form
# - Enable "Show Agent Dashboard"
# - Ask questions
# - Generate podcast
# - Check agent dashboard for A2A messages
```

---

## Need Help?

If something doesn't work:
1. Check terminal logs for errors
2. Check browser console (F12)
3. Verify all files are saved
4. Restart Streamlit app
5. Check `INTEGRATION_SUMMARY.md` for details
