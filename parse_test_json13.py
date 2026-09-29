# The user wants to build out the "Tools" settings UI or implementation.
# In `web/index.html` there is a Tools tab:
# <section id="tab-tools" class="tab-pane">
#   <div class="pane-header">
#       <h3>TOOL CONFIGURATION</h3>
#   </div>
#   <div class="settings-content">
#       <p class="placeholder-text">Available agent tools will be configured here.</p>
#   </div>
# </section>
#
# Right now, tools are hardcoded in `build_tools_array()` (weather, octoprint), and their scripts are just dummy prints.
# Each tool could have a config.json.
