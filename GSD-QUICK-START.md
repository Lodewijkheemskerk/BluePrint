# GSD Quick Start Guide

GSD (Get Shit Done) is now installed and configured for your BluePrint project!

## ✅ What's Been Set Up

- ✅ GSD commands installed in `.claude/commands/gsd/`
- ✅ Recommended permissions configured in `.claude/settings.json`
- ✅ Security: Sensitive files (`.env`, credentials) are protected from being read

## 🚀 Next Steps

### Step 1: Map Your Existing Codebase (Recommended First)

Since you have an existing project, start by mapping your codebase so GSD understands your architecture:

**In Cursor's chat, type:**
```
/gsd:map-codebase
```

This will:
- Analyze your FastAPI backend structure
- Understand your frontend architecture
- Map your database models and schemas
- Learn your coding conventions
- Document your tech stack (FastAPI, SQLAlchemy, ccxt, etc.)

### Step 2: Start Using GSD

After mapping, you can:

**For new features/milestones:**
```
/gsd:new-milestone
```

**For completely new projects:**
```
/gsd:new-project
```

**Quick ad-hoc tasks:**
```
/gsd:quick [description]
```

## 📋 Common Workflows

### Adding a New Feature
1. `/gsd:new-milestone` - Create a milestone for the feature
2. `/gsd:discuss-phase 1` - Refine implementation details
3. `/gsd:plan-phase 1` - Generate detailed implementation plan
4. `/gsd:execute-phase 1` - Build it!

### Debugging
```
/gsd:debug [description of issue]
```

### Check Progress
```
/gsd:progress
```

### View All Commands
```
/gsd:help
```

## ⚙️ Configuration

GSD settings are stored in `.planning/config.json` (created after first use).

**Change model profile (faster/cheaper):**
```
/gsd:set-profile budget
```

**Configure workflow:**
```
/gsd:settings
```

## 🔒 Security Note

Your `.env` files and credential files are protected from being read by GSD. This is configured in `.claude/settings.json`.

## 💡 Tips

- GSD works best when it understands your codebase - run `/gsd:map-codebase` first!
- Use `/gsd:quick` for simple tasks that don't need full planning
- The system automatically tracks your progress in `.planning/` directory
- All GSD files are git-tracked by default

---

**Ready to start?** Run `/gsd:map-codebase` in Cursor's chat!
