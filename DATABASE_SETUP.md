# Vexa Database Setup - Sharing with Nemrut

## Database Schema Analysis

### Vexa Tables (in `public` schema)
- `users` - Integer ID, email, name, max_concurrent_bots
- `api_tokens` - Links to Vexa users
- `meetings` - Meeting records
- `transcriptions` - Transcription segments
- `meeting_sessions` - Session tracking

### Nemrut Tables
- `public.accounts` - UUID, references `auth.users`
- `public.subscription_plans`
- `public.subscriptions`
- `public.trials`
- `public.feature_flags`
- `dms.*` - Document management tables (separate schema)

## ⚠️ Conflict Identified

**Both systems use a `users` table in the `public` schema, but they're incompatible:**

| Aspect | Vexa `users` | Nemrut `auth.users` |
|--------|--------------|---------------------|
| ID Type | Integer | UUID (Supabase) |
| Purpose | Vexa user management | Supabase Auth |
| Structure | Simple (email, name, bots) | Full auth system |

## ✅ Recommended Solutions

### Option 1: Separate Supabase Project (Recommended for Production)

**Pros:**
- ✅ Complete isolation
- ✅ No schema conflicts
- ✅ Independent scaling
- ✅ Easier backups/restores
- ✅ Clear separation of concerns

**Cons:**
- ⚠️ Additional Supabase project to manage
- ⚠️ Slightly higher cost (if not on free tier)

**Setup:**
1. Create new Supabase project: `vexa-production`
2. Use connection string from new project
3. Vexa will create its own tables automatically

### Option 2: Use Same Database with Schema Separation

**Pros:**
- ✅ Single database to manage
- ✅ Lower cost (one Supabase project)
- ✅ Shared connection pool

**Cons:**
- ⚠️ Requires modifying Vexa to use a different schema
- ⚠️ More complex setup
- ⚠️ Potential for confusion

**Setup:**
1. Create `vexa` schema in Nemrut's Supabase
2. Modify Vexa models to use `vexa` schema
3. Update database initialization

### Option 3: Use Same Database (Accept Risk)

**Pros:**
- ✅ Simplest setup
- ✅ Single database

**Cons:**
- ❌ **Table name conflict** - Both use `users` table
- ❌ **Data corruption risk** - Different ID types
- ❌ **Not recommended for production**

## 🎯 My Recommendation

**Use Option 1: Separate Supabase Project**

For production, I strongly recommend creating a dedicated Supabase project for Vexa:

1. **Isolation**: Vexa and Nemrut are separate services with different purposes
2. **Scalability**: Each can scale independently
3. **Security**: Clear boundaries between services
4. **Maintenance**: Easier to backup, restore, and manage
5. **Cost**: Free tier allows multiple projects

### Quick Setup

```bash
# 1. Create new Supabase project: "vexa-production"
# 2. Get connection string from Supabase dashboard
# 3. Use in Vexa deployment:

DATABASE_URL=postgresql://postgres.vexa_project_id:password@aws-0-us-west-2.pooler.supabase.com:5432/postgres
DB_SSL_MODE=require
```

## Alternative: Schema-Based Separation

If you must use the same database, we can modify Vexa to use a `vexa` schema:

1. Create migration to move Vexa tables to `vexa` schema
2. Update Vexa models to use schema prefix
3. Update database connection to use schema search path

**Would you like me to:**
- A) Set up separate Supabase project (recommended)
- B) Modify Vexa to use `vexa` schema in same database
- C) Something else?
