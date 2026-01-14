# Adding Avatar Support to Vexa - Implementation Plan

## Status

**This is NOT a lite version limitation** - it's simply a feature that hasn't been implemented in Vexa yet (open source or otherwise).

Since Vexa is **open source**, we can add this feature ourselves! ✅

## Implementation Steps

### Step 1: Add to Vexa Schema

**File:** `libs/shared-models/shared_models/schemas.py`

```python
class MeetingCreate(BaseModel):
    platform: Platform
    native_meeting_id: str
    bot_name: Optional[str] = Field(None, description="Optional name for the bot in the meeting")
    bot_avatar_url: Optional[str] = Field(None, description="Optional avatar URL for the bot")  # ADD THIS
    language: Optional[str] = None
    task: Optional[str] = None
    passcode: Optional[str] = None
```

### Step 2: Update Bot Manager

**File:** `services/bot-manager/app/main.py`

```python
# In request_bot function, extract bot_avatar_url from request
bot_avatar_url = req.bot_avatar_url  # ADD THIS

# Pass to start_bot_container
container_id, connection_id = await start_bot_container(
    # ... existing params ...
    bot_avatar_url=bot_avatar_url,  # ADD THIS
)
```

### Step 3: Update Orchestrator

**File:** `services/bot-manager/app/orchestrators/process.py`

```python
async def start_bot_container(
    user_id: int,
    meeting_id: int,
    meeting_url: Optional[str],
    platform: str,
    bot_name: Optional[str],
    bot_avatar_url: Optional[str] = None,  # ADD THIS
    user_token: str,
    native_meeting_id: str,
    language: Optional[str],
    task: Optional[str]
) -> Optional[Tuple[str, str]]:
    # ... existing code ...
    
    bot_config = {
        # ... existing fields ...
        "botName": bot_name or f"VexaBot-{uuid.uuid4().hex[:6]}",
        "botAvatarUrl": bot_avatar_url,  # ADD THIS
        # ... rest of config ...
    }
```

### Step 4: Update Bot TypeScript Types

**File:** `services/vexa-bot/core/src/types.ts`

```typescript
export type BotConfig = {
  platform: "google_meet" | "zoom" | "teams",
  meetingUrl: string | null,
  botName: string,
  botAvatarUrl?: string | null,  // ADD THIS
  token: string,
  connectionId: string,
  nativeMeetingId: string,
  language?: string | null,
  task?: string | null,
  redisUrl: string,
  container_name?: string,
  automaticLeave: {
    waitingRoomTimeout: number,
    noOneJoinedTimeout: number,
    everyoneLeftTimeout: number
  },
  reconnectionIntervalMs?: number,
  meeting_id: number,
  botManagerCallbackUrl?: string;
}
```

### Step 5: Implement Avatar Setting in Bot

**File:** `services/vexa-bot/core/src/platforms/google_meet/` (or wherever bot joins)

Need to:
1. Download avatar image from URL
2. Set as bot's profile picture in Google Meet
3. Handle errors gracefully (fallback to default)

**Google Meet API:**
- Google Meet uses the Google Account's profile picture
- For bots, we might need to:
  - Use Chrome extension API to set profile picture
  - Or inject image into the meeting UI
  - Or use Google Account API (if bot has a Google account)

## Implementation Complexity

**Easy Parts:**
- ✅ Adding schema field (5 min)
- ✅ Passing through bot-manager (10 min)
- ✅ Adding to bot_config (5 min)
- ✅ TypeScript types (2 min)

**Medium Parts:**
- ⚠️ Setting avatar in Google Meet (30-60 min)
  - Need to research Google Meet's avatar API
  - May require Chrome extension permissions
  - Or custom UI injection

**Total Estimated Time:** 1-2 hours

## Testing

1. Upload avatar in Nemrut
2. Create meeting
3. Verify avatar appears in Google Meet
4. Test with different image formats/sizes
5. Test error handling (invalid URL, network errors)

## Alternative: Quick Workaround

If setting avatar in Google Meet is complex, we could:
1. Store avatar URL in bot config (done)
2. Display avatar in Nemrut UI (already done)
3. Add avatar to meeting transcripts/reports (future)
4. Set avatar in Google Meet later (when we have time)

## Next Steps

1. ✅ Nemrut code ready (sends `bot_avatar_url`)
2. ⏳ Add to Vexa schema
3. ⏳ Pass through bot-manager
4. ⏳ Add to bot_config
5. ⏳ Implement in bot code
6. ⏳ Test

## Benefits of Adding This

- ✅ Better user experience
- ✅ Professional appearance
- ✅ Branding opportunities
- ✅ Competitive with paid solutions

Since we have the source code, we can add this feature whenever we want! 🚀
