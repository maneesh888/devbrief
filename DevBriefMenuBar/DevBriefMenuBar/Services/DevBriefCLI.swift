import Foundation

enum DevBriefCLIError: Error, LocalizedError {
    case binaryNotFound
    case nonZeroExit(Int32, String)

    var errorDescription: String? {
        switch self {
        case .binaryNotFound:
            return "devbrief CLI not found. Install it (see the README) so ~/.local/bin/devbrief exists, or set DEVBRIEF_BIN."
        case .nonZeroExit(let code, let stderr):
            return "devbrief exited \(code): \(stderr)"
        }
    }
}

enum DevBriefCLI {
    private static let candidateBinPaths = [
        NSHomeDirectory() + "/.local/bin/devbrief",
        "/opt/homebrew/bin/devbrief",
        "/usr/local/bin/devbrief",
    ]

    private static func resolveBin() -> String {
        if let override = ProcessInfo.processInfo.environment["DEVBRIEF_BIN"] { return override }
        return candidateBinPaths.first { FileManager.default.isExecutableFile(atPath: $0) }
            ?? candidateBinPaths[0]
    }

    @discardableResult
    private static func run(_ args: [String]) throws -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: resolveBin())
        process.arguments = args

        let outPipe = Pipe()
        let errPipe = Pipe()
        process.standardOutput = outPipe
        process.standardError = errPipe

        do {
            try process.run()
        } catch {
            throw DevBriefCLIError.binaryNotFound
        }
        process.waitUntilExit()

        let outData = outPipe.fileHandleForReading.readDataToEndOfFile()
        let errData = errPipe.fileHandleForReading.readDataToEndOfFile()
        let out = String(data: outData, encoding: .utf8) ?? ""
        let err = String(data: errData, encoding: .utf8) ?? ""

        guard process.terminationStatus == 0 else {
            throw DevBriefCLIError.nonZeroExit(process.terminationStatus, err)
        }
        return out
    }

    /// date: "YYYY-MM-DD", or nil for today (devbrief's own default).
    static func generate(date: String? = nil) throws -> String {
        var args = ["generate"]
        if let date { args += ["--date", date] }
        return try run(args)
    }

    /// Dry run: same as `generate`, but devbrief never touches the log or
    /// checkpoint. Output is in the same format as `log`, so it's parsed
    /// the same way.
    static func preview(date: String? = nil) throws -> [LogEntry] {
        var args = ["generate", "--preview"]
        if let date { args += ["--date", date] }
        return parseLogOutput(try run(args))
    }

    static func clearAll() throws {
        try run(["clear", "--yes"])
    }

    static func defaultPrompt() throws -> String {
        try run(["prompt"]).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Parses `devbrief sources list`'s "[x] name" / "[ ] name" lines.
    static func listSources() throws -> [String: Bool] {
        let output = try run(["sources", "list"])
        var result: [String: Bool] = [:]
        for rawLine in output.split(separator: "\n") {
            let line = rawLine.trimmingCharacters(in: .whitespaces)
            guard line.hasPrefix("[x]") || line.hasPrefix("[ ]") else { continue }
            let name = line.dropFirst(3).trimmingCharacters(in: .whitespaces)
            result[name] = line.hasPrefix("[x]")
        }
        return result
    }

    static func setSource(_ name: String, enabled: Bool) throws {
        try run(["sources", "set", name, enabled ? "on" : "off"])
    }

    static func fetchLog(limit: Int = 10) throws -> [LogEntry] {
        let output = try run(["log", "--limit", "\(limit)"])
        return parseLogOutput(output)
    }

    /// Parses devbrief's plain-text `log` output:
    /// "=== 2026-10-16 | project | /full/repo/path ===\n<text>\n\n"
    private static func parseLogOutput(_ output: String) -> [LogEntry] {
        var entries: [LogEntry] = []
        let lines = output.components(separatedBy: "\n")
        var i = 0
        while i < lines.count {
            let line = lines[i]
            if line.hasPrefix("=== "), line.hasSuffix(" ===") {
                let inner = line.dropFirst(4).dropLast(4)
                let parts = inner.components(separatedBy: " | ")
                i += 1
                var textLines: [String] = []
                while i < lines.count, !lines[i].isEmpty {
                    textLines.append(lines[i])
                    i += 1
                }
                if parts.count == 3 {
                    entries.append(LogEntry(
                        date: parts[0], project: parts[1], repoRoot: parts[2],
                        text: textLines.joined(separator: "\n")
                    ))
                }
            } else {
                i += 1
            }
        }
        return entries
    }
}
