import Foundation
import Combine

class RollcallViewModel: ObservableObject {
    @Published var remainingSeconds: Int = 0
    @Published var currentQr: String = "--"
    @Published var connectedEdges: Int = 0
    @Published var uncheckinEdges: Int = 0
    @Published var isExpired: Bool = false
    @Published var isSubmitting: Bool = false
    @Published var toastMessage: String?
    @Published var isSuccess: Bool = true
    
    private var webSocketTask: URLSessionWebSocketTask?
    private let baseURL = "https://cqupt.ishub.top"
    private let wsURL = "wss://cqupt.ishub.top/api/rollcall/ws/status"
    
    init() {
        connectWebSocket()
    }
    
    func connectWebSocket() {
        guard let url = URL(string: wsURL) else { return }
        let session = URLSession(configuration: .default)
        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()
        receiveMessage()
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self?.handleWSMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self?.handleWSMessage(text)
                    }
                @unknown default:
                    break
                }
                self?.receiveMessage()
            case .failure(let error):
                print("WebSocket error: \(error)")
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                    self?.connectWebSocket()
                }
            }
        }
    }
    
    private func handleWSMessage(_ text: String) {
        guard let data = text.data(using: .utf8) else { return }
        do {
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                DispatchQueue.main.async {
                    self.remainingSeconds = json["remaining_seconds"] as? Int ?? 0
                    self.currentQr = json["current_qr"] as? String ?? "--"
                    self.connectedEdges = json["connected_edges"] as? Int ?? 0
                    self.uncheckinEdges = json["uncheckin_edges"] as? Int ?? 0
                    self.isExpired = self.remainingSeconds <= 0
                }
            }
        } catch {
            print("Failed to decode WS message: \(error)")
        }
    }
    
    func submitQr(rawData: String) {
        let extracted = extractQrData(rawData)
        
        // Regex: /^[a-f0-9]{42}$/i
        let regex = try! NSRegularExpression(pattern: "^[a-f0-9]{42}$", options: .caseInsensitive)
        let range = NSRange(location: 0, length: extracted.utf16.count)
        if regex.firstMatch(in: extracted, options: [], range: range) == nil {
            showToast("非有效签到码", success: false)
            return
        }
        
        guard let url = URL(string: "\(baseURL)/api/rollcall/qr") else { return }
        
        isSubmitting = true
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = ["data": extracted]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                self?.isSubmitting = false
                if let error = error {
                    self?.showToast("网络错误: \(error.localizedDescription)", success: false)
                    return
                }
                
                guard let data = data else {
                    self?.showToast("服务器无响应", success: false)
                    return
                }
                
                do {
                    if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                        if json["message"] as? String == "success" {
                            self?.showToast("提交成功", success: true)
                        } else {
                            let errorMsg = json["error"] as? String ?? "提交失败"
                            self?.showToast(errorMsg, success: false)
                        }
                    }
                } catch {
                    self?.showToast("解析错误", success: false)
                }
            }
        }.resume()
    }
    
    private func extractQrData(_ rawData: String) -> String {
        if rawData.contains("/j?p=") {
            let regex = try! NSRegularExpression(pattern: "!3~([a-f0-9]+)", options: .caseInsensitive)
            let range = NSRange(location: 0, length: rawData.utf16.count)
            if let match = regex.firstMatch(in: rawData, options: [], range: range) {
                if let qrRange = Range(match.range(at: 1), in: rawData) {
                    return String(rawData[qrRange])
                }
            }
        }
        return rawData
    }
    
    private func showToast(_ message: String, success: Bool) {
        self.toastMessage = message
        self.isSuccess = success
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
            if self.toastMessage == message {
                self.toastMessage = nil
            }
        }
    }
}
