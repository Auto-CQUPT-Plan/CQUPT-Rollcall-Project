import SwiftUI
import VisionKit
import Vision

struct QRScannerView: UIViewControllerRepresentable {
    var didFindCode: (String) -> Void
    
    func makeUIViewController(context: Context) -> DataScannerViewController {
        // 实例化原生的数据扫描器
        let scanner = DataScannerViewController(
            recognizedDataTypes: [.barcode(symbologies: [.qr])],
            qualityLevel: .balanced,
            recognizesMultipleItems: false,
            isHighFrameRateTrackingEnabled: true,
            isHighlightingEnabled: true // 自动在二维码上显示高亮框
        )
        scanner.delegate = context.coordinator
        return scanner
    }
    
    func updateUIViewController(_ uiViewController: DataScannerViewController, context: Context) {
        // 尝试启动扫描
        try? uiViewController.startScanning()
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(didFindCode: didFindCode)
    }
    
    class Coordinator: NSObject, DataScannerViewControllerDelegate {
        var didFindCode: (String) -> Void
        
        init(didFindCode: @escaping (String) -> Void) {
            self.didFindCode = didFindCode
        }
        
        func dataScanner(_ dataScanner: DataScannerViewController, didTapOn item: RecognizedItem) {
            switch item {
            case .barcode(let code):
                if let stringValue = code.payloadStringValue {
                    processCode(stringValue)
                }
            default: break
            }
        }
        
        func dataScanner(_ dataScanner: DataScannerViewController, didAdd addedItems: [RecognizedItem], allItems: [RecognizedItem]) {
            // 如果自动识别到了
            if let firstCode = addedItems.first {
                switch firstCode {
                case .barcode(let code):
                    if let stringValue = code.payloadStringValue {
                        processCode(stringValue)
                    }
                default: break
                }
            }
        }
        
        private func processCode(_ code: String) {
            // 触感反馈
            let generator = UINotificationFeedbackGenerator()
            generator.notificationOccurred(.success)
            
            DispatchQueue.main.async {
                self.didFindCode(code)
            }
        }
    }
}
