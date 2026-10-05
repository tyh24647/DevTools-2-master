#!/usr/bin/env python3
"""Validate generated project structure and plists using only Python's standard library."""
from pathlib import Path
import re
import json
import plistlib

root = Path(__file__).resolve().parents[1]
source = (root / 'DevTools.xcodeproj/project.pbxproj').read_text()
pattern = re.compile(r'\s+|//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[{}()=;,]|[A-Za-z0-9_.$<>/@+-]+', re.S)
tokens = []
position = 0
for match in pattern.finditer(source):
    assert match.start() == position, 'Unrecognized project text at ' + str(position)
    position = match.end()
    token = match.group()
    if not token.isspace() and not token.startswith('//') and not token.startswith('/*'):
        tokens.append(token)
assert position == len(source)
cursor = 0

def take(expected=None):
    global cursor
    value = tokens[cursor]
    cursor += 1
    if expected is not None:
        assert value == expected, (value, expected, cursor)
    return value

def value():
    token = take()
    if token == '{':
        result = {}
        while tokens[cursor] != '}':
            key = value()
            take('=')
            result[key] = value()
            take(';')
        take('}')
        return result
    if token == '(':
        result = []
        while tokens[cursor] != ')':
            result.append(value())
            take(',')
        take(')')
        return result
    if token.startswith('"'):
        return json.loads(token)
    return int(token) if token.isdigit() else token

project = value()
assert cursor == len(tokens)
objects = project['objects']
assert objects[project['rootObject']]['isa'] == 'PBXProject'
targets = [obj for obj in objects.values() if obj['isa'] == 'PBXNativeTarget']
assert len(targets) == 8
missing = []
for obj in objects.values():
    if obj['isa'] == 'PBXFileReference' and obj.get('sourceTree') == '<group>':
        if not (root / obj['path']).exists():
            missing.append(obj['path'])
assert not missing, 'Missing referenced files: ' + repr(missing)

app = next(target for target in targets if target['name'] == 'DevTools')
assert len(app['dependencies']) == 7
embed = [objects[key] for key in app['buildPhases'] if objects[key]['isa'] == 'PBXCopyFilesBuildPhase']
assert len(embed) == 1 and len(embed[0]['files']) == 7 and embed[0]['dstSubfolderSpec'] == 13

for target in targets:
    settings = objects[objects[target['buildConfigurationList']]['buildConfigurations'][0]]['buildSettings']
    assert settings['CODE_SIGN_ENTITLEMENTS'] == 'Configuration/Shared.entitlements'
    plist = plistlib.loads((root / settings['INFOPLIST_FILE']).read_bytes())
    assert plist['DevToolsAppGroup'] == '$(DT_APP_GROUP)'
    for phaseID in target['buildPhases']:
        phase = objects[phaseID]
        if phase['isa'] in ('PBXSourcesBuildPhase', 'PBXResourcesBuildPhase'):
            for buildID in phase['files']:
                fileID = objects[buildID]['fileRef']
                assert (root / objects[fileID]['path']).exists()
        if target['name'] != 'DevTools' and phase['isa'] == 'PBXFrameworksBuildPhase':
            assert phase['files'] == [], 'Advertising must not be linked to extensions.'
    if target['name'] not in ('DevTools', 'DevToolsSafari'):
        extension = plist['NSExtension']
        assert extension['NSExtensionPointIdentifier'] == 'com.apple.ui-services'
        assert extension['NSExtensionAttributes']['NSExtensionJavaScriptPreprocessingFile'] == 'Action'

for path in (root / 'Configuration').glob('*.plist'):
    plistlib.loads(path.read_bytes())
plistlib.loads((root / 'Configuration/Shared.entitlements').read_bytes())
plistlib.loads((root / 'Shared/PrivacyInfo.xcprivacy').read_bytes())
storekit = json.loads((root / 'Configuration/DevTools.storekit').read_text())
assert storekit['products'][0]['displayPrice'] == '19.99'
assert storekit['subscriptionGroups'][0]['subscriptions'][0]['displayPrice'] == '2.99'
catalog = json.loads((root / 'Shared/tool-catalog.json').read_text())
assert len(catalog['assets']) == 10
print('Validated 8 targets, 7 embedded extensions, shared entitlements, resources, plists and test pricing.')
