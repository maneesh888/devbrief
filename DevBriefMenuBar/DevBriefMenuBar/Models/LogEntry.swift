import Foundation

struct LogEntry: Identifiable {
    let id = UUID()
    let date: String
    let project: String
    let repoRoot: String
    let text: String
}
