import AppKit

/// Writes preview results to a throwaway text file and opens it in the default
/// editor. The file lives in a dedicated temp folder that is wiped on the next
/// preview, on app launch/quit, and after `lifetime` seconds.
enum PreviewFile {
    private static let lifetime: TimeInterval = 600
    private static let directory = URL(fileURLWithPath: NSTemporaryDirectory())
        .appendingPathComponent("devbrief-preview", isDirectory: true)

    static func open(_ entries: [LogEntry]) throws {
        cleanUp()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let file = directory.appendingPathComponent("devbrief-preview-\(Int(Date().timeIntervalSince1970)).txt")
        try render(entries).write(to: file, atomically: true, encoding: .utf8)
        NSWorkspace.shared.open(file)

        NotificationCenter.default.addObserver(
            forName: NSApplication.willTerminateNotification, object: nil, queue: nil
        ) { _ in cleanUp() }
        DispatchQueue.main.asyncAfter(deadline: .now() + lifetime) { try? FileManager.default.removeItem(at: file) }
    }

    static func cleanUp() {
        try? FileManager.default.removeItem(at: directory)
    }

    private static func render(_ entries: [LogEntry]) -> String {
        guard !entries.isEmpty else { return "No activity found for the selected range.\n" }
        let multipleProjects = Set(entries.map(\.project)).count > 1
        return DayGroup.group(entries).map { group in
            let body = group.entries.map { entry in
                multipleProjects ? "[\(entry.project)]\n\(entry.text)" : entry.text
            }.joined(separator: "\n\n")
            return "\(group.title)\n\(body)"
        }.joined(separator: "\n\n") + "\n"
    }
}
