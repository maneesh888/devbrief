import Foundation

enum LaunchAgentError: Error, LocalizedError {
    case plistMissing
    case commandFailed(String)

    var errorDescription: String? {
        switch self {
        case .plistMissing:
            return "LaunchAgent plist not installed at ~/Library/LaunchAgents yet."
        case .commandFailed(let message):
            return "launchctl failed: \(message)"
        }
    }
}

enum LaunchAgentController {
    static let label = "com.maneesh.devbrief.daily"

    static var plistPath: String {
        NSHomeDirectory() + "/Library/LaunchAgents/\(label).plist"
    }

    static func isLoaded() -> Bool {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        process.arguments = ["list", label]
        process.standardOutput = Pipe()
        process.standardError = Pipe()
        guard (try? process.run()) != nil else { return false }
        process.waitUntilExit()
        return process.terminationStatus == 0
    }

    static func setLoaded(_ loaded: Bool) throws {
        guard FileManager.default.fileExists(atPath: plistPath) else {
            throw LaunchAgentError.plistMissing
        }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        process.arguments = [loaded ? "load" : "unload", plistPath]
        let errPipe = Pipe()
        process.standardError = errPipe

        try process.run()
        process.waitUntilExit()

        guard process.terminationStatus == 0 else {
            let errData = errPipe.fileHandleForReading.readDataToEndOfFile()
            throw LaunchAgentError.commandFailed(String(data: errData, encoding: .utf8) ?? "")
        }
    }
}
