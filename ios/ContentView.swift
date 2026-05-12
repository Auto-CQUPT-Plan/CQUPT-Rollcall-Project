import SwiftUI

struct ContentView: View {
    @StateObject var viewModel = RollcallViewModel()
    @State private var showingScanner = false
    
    var body: some View {
        NavigationView {
            ZStack {
                ScrollView {
                    VStack(spacing: 24) {
                        StatusCardView(viewModel: viewModel)
                            .padding(.top)
                        
                        VStack(alignment: .leading, spacing: 8) {
                            Text("当前签到码")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                            
                            Text(viewModel.currentQr.isEmpty ? "无" : viewModel.currentQr)
                                .font(.title3)
                                .padding()
                                .frame(maxWidth: .infinity)
                                .background(Color(.secondarySystemBackground))
                                .cornerRadius(8)
                        }
                        .padding(.horizontal)
                        
                        Spacer(minLength: 50)
                        
                        Button(action: {
                            showingScanner = true
                        }) {
                            Text("扫一扫签到")
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                        .padding(.horizontal)
                    }
                }
                
                if viewModel.isSubmitting {
                    ZStack {
                        Color.black.opacity(0.2).edgesIgnoringSafeArea(.all)
                        VStack {
                            ProgressView()
                            Text("正在提交...")
                        }
                        .padding()
                        .background(Color(.systemBackground))
                        .cornerRadius(8)
                    }
                }
                
                if let message = viewModel.toastMessage {
                    ToastView(message: message, isSuccess: viewModel.isSuccess)
                }
            }
            .navigationTitle("签到看板")
            .sheet(isPresented: $showingScanner) {
                ScannerSheet(viewModel: viewModel, isPresented: $showingScanner)
            }
        }
    }
}

struct StatusCardView: View {
    @ObservedObject var viewModel: RollcallViewModel
    
    var body: some View {
        HStack {
            StatusItem(
                title: "有效时间",
                value: viewModel.isExpired ? "已过期" : "\(viewModel.remainingSeconds)s",
                color: viewModel.isExpired ? .red : .green
            )
            Divider().frame(height: 30)
            StatusItem(
                title: "待签到",
                value: "\(viewModel.uncheckinEdges)",
                color: .orange
            )
            Divider().frame(height: 30)
            StatusItem(
                title: "已连接",
                value: "\(viewModel.connectedEdges)",
                color: .blue
            )
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(8)
        .padding(.horizontal)
    }
}

struct StatusItem: View {
    let title: String
    let value: String
    var color: Color = .primary
    
    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.headline)
                .foregroundColor(color)
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

struct ScannerSheet: View {
    @ObservedObject var viewModel: RollcallViewModel
    @Binding var isPresented: Bool
    
    var body: some View {
        ZStack {
            QRScannerView { code in
                isPresented = false
                viewModel.submitQr(rawData: code)
            }
            .edgesIgnoringSafeArea(.all)
            
            VStack {
                HStack {
                    Button("关闭") {
                        isPresented = false
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.gray)
                    .padding()
                    
                    Spacer()
                }
                Spacer()
            }
        }
    }
}

struct ToastView: View {
    let message: String
    let isSuccess: Bool
    
    var body: some View {
        VStack {
            Spacer()
            Text(message)
                .foregroundColor(isSuccess ? .green : .red)
                .padding()
                .background(Color(.systemBackground))
                .cornerRadius(8)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color.primary.opacity(0.1), lineWidth: 1)
                )
                .padding(.bottom, 50)
        }
    }
}
