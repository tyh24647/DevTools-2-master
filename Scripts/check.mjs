import fs from "node:fs/promises";
import path from "node:path";
import vm from "node:vm";
import xcode from "xcode";
import assert from "node:assert/strict";

const root = path.resolve(import.meta.dirname, "..");
const resources = path.join(root, "SafariExtension/Resources");
const manifest = JSON.parse(await fs.readFile(path.join(resources, "manifest.json"), "utf8"));
const catalog = JSON.parse(await fs.readFile(path.join(resources, "tool-catalog.json"), "utf8"));
const required = [
    ...manifest.background.scripts,
    ...manifest.content_scripts.flatMap((x) => x.js),
    manifest.action.default_popup,
    ...Object.values(manifest.icons),
    ...catalog.assets.map((x) => x.file)
];
for (const file of required) {
    await fs.access(path.join(resources, file));
}
for (const file of (await fs.readdir(resources)).filter((name) => name.endsWith(".js"))) {
    new vm.Script(await fs.readFile(path.join(resources, file), "utf8"), { filename: file });
}
new vm.Script(await fs.readFile(path.join(root, "ActionExtension/Action.js"), "utf8"));
for (const asset of catalog.assets) {
    new vm.Script(await fs.readFile(path.join(resources, asset.file), "utf8"), { filename: asset.file });
}
console.log("Validated MV3 resources, script syntax and " + catalog.assets.length + " bundled packages.");

const project = xcode.project(path.join(root, "DevTools.xcodeproj/project.pbxproj"));
project.parseSync();
const targets = Object.values(project.hash.project.objects).filter(
    (object) => object.isa === "PBXNativeTarget"
);
assert.equal(targets.length, 8);
console.log("Parsed the Xcode project with eight native targets.");
