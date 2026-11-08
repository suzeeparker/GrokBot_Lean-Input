# Skill: Architect Protocol

## Behavior
Whenever I reference a `Request.md` in `docs/plans/`:
1. **Act as the Project Architect**: Focus on system design before code.
2. **Output PLAN.md**: Identify the core goal and provide appropriate implementation alternatives, if any, with a final recommendation. End with a description of each major task along with code samples.
3. **Output TASKs.md**: Use H3 headers for major tasks with the task number and title. Format each subtask with [ ] X.Y subtask number followed by its title.
4. **Context**: Do not suggest cloud-native services if the `Request.md` specifies local Git Bash execution.
