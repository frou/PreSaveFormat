import os
import os.path
import re
import sublime
import sublime_plugin
import subprocess



#### COMMAND ####


class ElmFormatCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        region = sublime.Region(0, self.view.size())
        content = self.view.substr(region)

        stdout, stderr = subprocess.Popen(
            ["elm-format", '--stdin', '--yes'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=os.name=="nt").communicate(input=bytes(content, 'UTF-8'))

        if stderr.strip():
            open_panel(self.view, re.sub('\x1b\[\d{1,2}m', '', stderr.strip().decode()))
        else:
            self.view.replace(edit, region, stdout.decode('UTF-8'))
            self.view.window().run_command("hide_panel", {"panel": "output.elm_format"})



#### ON SAVE ####


class ElmFormatOnSave(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        scope = view.scope_name(0)
        if scope.find('source.elm') != -1 and needs_format(view):
            view.run_command('elm_format')


def needs_format(view):
    settings = sublime.load_settings('elm-format-on-save.sublime-settings')
    on_save = settings.get('on_save', True)

    if isinstance(on_save, bool):
        return on_save

    if isinstance(on_save, dict):
        path = view.file_name()
        included = is_included(on_save, path)
        excluded = is_excluded(on_save, path)
        if isinstance(included, bool) and isinstance(excluded, bool):
            return included and not excluded

    open_panel(view, invalid_settings)
    return False


def is_included(on_save, path):
    if "including" in on_save:
        if not isinstance(on_save.get("including"), list):
            return None

        for string in on_save.get("including"):
            if string in path:
                return True

        return False

    return True


def is_excluded(on_save, path):
    if "excluding" in on_save:
        if not isinstance(on_save.get("excluding"), list):
            return None

        for string in on_save.get("excluding"):
            if string in path:
                return True

        return False

    return False


#### ERROR MESSAGES ####

# @todo #0 Don't show elm-format errors in a panel, since they aren't navigable using keyboard shortcuts like build system compiler errrors are.
#  Instead, just show a message like "ELM-FORMAT FAILED - SEE CONSOLE" in the status bar, and print() the error to the console in case we want to look at it. In most cases, we will probably instead run Build and see the errors that way.


def open_panel(view, content):
    window = view.window()
    panel = window.create_output_panel("elm_format")
    panel.set_read_only(False)
    panel.run_command('erase_view')
    panel.run_command('append', {'characters': content})
    panel.set_read_only(True)
    window.run_command("show_panel", {"panel": "output.elm_format"})



#### ERROR MESSAGES ####


def cannot_find_elm_format():
    return """-- ELM-FORMAT NOT FOUND -----------------------------------------------

I tried run elm-format, but I could not find it on your computer.

Try the recommendations from:

  https://github.com/evancz/elm-format-on-save/blob/master/troubleshooting.md

If everything fails, just remove the "elm-format-on-save" plugin from
your editor via Package Control. Sometimes it is not worth the trouble.

-----------------------------------------------------------------------

NOTE: Your PATH variable led me to check in the following directories:

    """ + '\n    '.join(os.environ['PATH'].split(os.pathsep)) + """

But I could not find `elm-format` in any of them. Please let me know
at https://github.com/evancz/elm-format-on-save/issues if this does
not seem correct!
"""


invalid_settings = """-- INVALID SETTINGS ---------------------------------------------------

The "on_save" field in your settings is invalid.

For help, check out the section on including/excluding files within:

  https://github.com/evancz/elm-format-on-save/blob/master/README.md

-----------------------------------------------------------------------
"""
