# If we set tool_choice="auto" on the recurse, the grammar allows `{`. If the model outputs `{`, it doesn't crash LM Studio.
# But it MIGHT output a real tool_call object again, which our loop won't process (because we don't recurse recursively).
# But at least it won't crash LM Studio.
# AND we can add a system message right before the recurse to strongly discourage it from doing so.
# Let's replace `kwargs2["tool_choice"] = "none"` with `kwargs2["tool_choice"] = "auto"`.
