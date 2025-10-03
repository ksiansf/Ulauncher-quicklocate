import subprocess
import os
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction

# Path to fdfind binary (adjust if installed elsewhere)
FDFIND_BIN = '/usr/bin/fdfind'

def find(search, path='~', extra=''):
    import os
    path = os.path.expanduser(path)
    cmd = f'cd "{path}" && /usr/bin/fdfind -a {extra} "{search}"'
    
    # Write the command to a temp log to debug
    with open('/tmp/quickfind_debug.log', 'a') as f:
        f.write(f'Executing: {cmd}\n')
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    with open('/tmp/quickfind_debug.log', 'a') as f:
        f.write(f'STDOUT: {result.stdout}\nSTDERR: {result.stderr}\n\n')
    
    return [i for i in result.stdout.splitlines()]


def get_item(path, name=None, desc=''):
    return ExtensionResultItem(
        icon='images/icon.png',
        name=name if name else path,
        description=desc,
        on_enter=RunScriptAction(f'xdg-open "{path}"', [])
    )

class DemoExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())

class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_argument()
        keyword = event.get_keyword()

        fd_keyword = extension.preferences.get('fd')
        fdir_keyword = extension.preferences.get('fdir')
        search_path = extension.preferences.get('dir')
        cut_off = int(extension.preferences.get('cut'))
        show_dirs = extension.preferences.get('show_dirs').lower().replace('\n', '') == 'yes'

        found = []
        if fd_keyword == keyword:
            found = find(data, path=search_path)
        elif fdir_keyword == keyword:
            found = find(data, path=search_path, extra='-t d')

        items = []
        i = 0

        while len(items) < cut_off and i < len(found):
            path = found[i]
            items.append(get_item(path))

            new_path = "/".join(path.split('/')[:-1]) + '/'
            if len(items) < cut_off and not path.endswith('/') and show_dirs:
                items.append(get_item(new_path, name=f'↑Dir: {new_path}', desc='Directory of the file above'))
                i += 1

            i += 1

        return RenderResultListAction(items)

if __name__ == '__main__':
    DemoExtension().run()
