# Dashboard Real-Time Updates Limitation

## Current Behavior

The agent dashboard **does appear immediately** when you ask a question, but it shows the **initial state** and stays there until processing completes.

## Why It Gets "Stuck"

1. **Streamlit Limitation**: Streamlit only reruns the app after a function completes
2. **Blocking Operation**: `graph.invoke()` is a blocking call that runs all agents synchronously
3. **No Refresh During Processing**: Streamlit can't refresh the UI while `graph.invoke()` is running

## What You See

- ✅ Dashboard appears immediately with "Received query, initializing..."
- ✅ Shows initial metrics (all "Pending")
- ⚠️ **Stays on initial state** during processing (this is the "stuck" behavior)
- ✅ Updates to final state when processing completes
- ✅ Disappears when answer is ready

## Current Status

- **A2A Framework**: ✅ Working - Messages are being sent
- **MCP Fallback**: ✅ Working - Available as fallback
- **AG-UI Dashboard**: ✅ Shows - But doesn't update during processing (Streamlit limitation)

## Solution for Real-Time Updates

To get **true real-time updates** during processing, we would need to:

1. Use LangGraph's `astream_events()` API (async streaming)
2. Run processing in a background thread
3. Use Streamlit's `st.rerun()` in a loop with state polling

This is a **significant architectural change** and would require:
- Async/await handling
- Background thread management
- State polling mechanism
- More complex error handling

## Workaround

For now, the dashboard:
- Shows immediately when you ask a question ✅
- Shows the final state when processing completes ✅
- Shows A2A messages that were created during processing ✅
- Disappears when answer is ready ✅

The "stuck" behavior is expected due to Streamlit's synchronous execution model.

## Verification

To verify A2A and MCP are working:

1. **Check Terminal Logs**: Look for "Sending A2A message" entries
2. **Check Final Dashboard**: After processing, dashboard shows final state with A2A messages
3. **Check Podcast Generation**: MCP fallback activates if OpenAI TTS fails

All three frameworks (A2A, MCP, AG-UI) are **implemented and working**, but real-time dashboard updates during processing require async streaming (future enhancement).
