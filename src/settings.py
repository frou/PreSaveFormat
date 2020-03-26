import sublime


def pkg_settings():
    return sublime.load_settings("PreSaveFormat.sublime-settings")


PKG_SETTINGS_KEY_ENABLED = "enabled"
PKG_SETTINGS_KEY_INCLUDE = "include"
PKG_SETTINGS_KEY_EXCLUDE = "exclude"
