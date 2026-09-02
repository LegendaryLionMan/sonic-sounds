# Mixtape '85 Study Plan

## Purpose
This study plan helps you deepen your understanding of the Mixtape '85 design system, user language patterns, and how to leverage the album-studio workflow for creative development. It is not a technical task — it's a cognitive companion for your creative work.

## Core Components

### 1. Design System Literacy
- **Typography**: Inter (body), Bebas Neue (headlines), Caveat (leads), JetBrains Mono (code), monospaced UI
- **Color Theory**: 
  - Primary: --ink (#fafafa), --bg (#0a0a0f) 
  - Accent: --red (#e83a3a), --yellow (#f0c53c), --cyan (#2dd8f0), --green (#4caf50), --blue (#2962ff), --magenta (#f25cb0), --violet (#b94af5), --amber (#ff7b00)
  - Usage: 60% neutral, 30% accent, 10% highlight
- **Spacing System**: 8px base unit (24px = 3rem, 48px = 6rem, 96px = 12rem)
- **Component Pattern**: 
  - Cards: 16px padding, 12px gap, 8px radius
  - Buttons: 56px height, 8px gap, 12px padding
  - Cards: 14px border, 12px radius, 24px grid gap

### 2. User Language Patterns
- **User Preferences**: 
  - "never assume" → verify before building
  - "local-first" → SQLite over cloud services
  - "honest architecture" → no half-measures
  - "terse but complete" → DO + VERIFY + REPORT
- **Communication Style**: 
  - Direct questions: "what did I ask?" not "can you explain?"
  - Context-aware: "continue from here" not "start fresh"
  - Technical precision: "threading.local()" vs "module-level dict"
- **Workflow Preferences**: 
  - "go faster" = minimal narration during build mode
  - "stop too much" = less commentary, more execution
  - "check facts" → verify before proposing solutions

### 3. Workflow Integration
- **Session Lifecycle**: 
  - 12h auto-pause → studio session → album creation → event logging → decision logging
  - Daily rhythm: planning → build → test → deploy → review
- **Toolchain Integration**: 
  - Use Studio page for session management
  - Use events/decisions for creative logging
  - Use studio.js for real-time session state
  - Use albums.js for album management

### 4. Cognitive Patterns
- **Problem-Solving**: 
  - Identify the actual problem (not the stated one)
  - Verify system state before proposing changes
  - Test in isolation before integration
  - Document the fix for future reference
- **Design Thinking**: 
  - Start with the user's stated goal
  - Map to existing patterns (sessions, events, decisions)
  - Propose minimal viable implementation
  - Validate with tests before shipping

### 5. Practice Exercises
1. **Recap**: After reading any documentation, summarize in 1-3 sentences what you understood
2. **Pattern Matching**: Find 3 similar patterns in your current work vs. Mixtape '85 patterns
3. **Language Audit**: Review one user message for emphasis, recap-test phrasing, and technical precision
4. **Workflow Check**: Before starting a new task, verify:
   - Is this a new feature or a refinement?
   - Do I have the right tools (local vs cloud)?
   - Are there existing patterns I should follow?

### 6. Key Insights from Mixtape '85
- **Consistency > Creativity**: The design system works because it's predictable, not because it's flashy
- **State is King**: Every UI state (active/paused/idle) has a defined path
- **Progressive Enhancement**: Start simple, add complexity only when needed
- **Error as Signal**: System errors are diagnostic tools, not failures
- **Time as Metric**: 12h idle auto-pause is a feature, not a bug

### 7. Practical Exercises
1. **Recap Exercise**: After reading any documentation, write 1-3 sentences summarizing what you learned
2. **Pattern Hunt**: Find 3 instances of the same pattern (e.g., card layout, status badge) across the site
3. **Language Audit**: Pick one user message and identify its recap-test pattern
4. **Workflow Check**: Before starting a new task, ask:
   - Is this a new feature or refinement?
   - Do I have the right tools (local vs cloud)?
   - What pattern does this align with?

### 8. Key Takeaways
- **Consistency is Power**: The same patterns apply across UI, API, and testing
- **State Awareness**: The system tracks state (active/paused/done) at every level
- **Autonomy with Guidance**: You control the workflow but follow established patterns
- **Feedback Loop**: Tests → Code → Design → User → Test → Repeat

### 9. Next Steps
1. Read the plan.md files for Days 1-5
2. Review the studio.html and albums.html pages side-by-side
3. Run the full test suite to confirm stability
4. Use the study plan to deepen your understanding of the design principles
5. When ready, propose Day 6 or other creative extensions