import Foundation

enum PromptStore {
    static var overridePath: String {
        NSHomeDirectory() + "/.devbrief/prompt_override.txt"
    }

    static func loadOverride() -> String {
        (try? String(contentsOfFile: overridePath, encoding: .utf8)) ?? ""
    }

    static func save(_ text: String) throws {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let dir = (overridePath as NSString).deletingLastPathComponent
        try FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        try trimmed.write(toFile: overridePath, atomically: true, encoding: .utf8)
    }

    static func resetToDefault() throws {
        guard FileManager.default.fileExists(atPath: overridePath) else { return }
        try FileManager.default.removeItem(atPath: overridePath)
    }
}
