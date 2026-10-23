import Foundation

enum DevBriefCLIError: Error, LocalizedError {
    case binaryNotFound
    case nonZeroExit(Int32, String)

    var errorDescription: String? {
        switch self {
        case .binaryNotFound:
            return "devbrief CLI not found. Set DEVBRIEF_BIN or check the install path."
        case .nonZeroExit(let code, let stderr):
            return "devbrief exited \(code): \(stderr)"
        }
    }
}

enum DevBriefCLI {
    private static let defaultBinPath = "/usr/local/bin/devbrief"

    private static func resolveBin() -> String {
        ProcessInfo.processInfo.environment["DEVBRIEF_BIN"] ?? defaultBinPath
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

    static func clearAll() throws {
        try run(["clear", "--yes"])
    }

    static func defaultPrompt() throws -> String {
        try run(["prompt"]).trimmingCharacters(in: .whitespacesAndNewlines)
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
