#!/usr/bin/env python3
# coding: utf-8
"""
SenseVoice 性能对比测试工具
对比 PyTorch (.pt) 模型 vs ONNX 模型的性能差异

测试指标：
1. 服务启动时间
2. 模型加载时间  
3. 首次推理时间（冷启动）
4. 平均推理时间（热启动）
5. 内存使用情况
6. CPU使用情况
"""

import os
import sys
import time
import json
import requests
import subprocess
import threading
import psutil
from pathlib import Path
from typing import Dict, List
import matplotlib.pyplot as plt
import pandas as pd

class PerformanceMonitor:
    def __init__(self):
        self.cpu_usage = []
        self.memory_usage = []
        self.timestamps = []
        self.monitoring = False
        self.process = None
    
    def start_monitoring(self, pid):
        """开始监控进程性能"""
        self.process = psutil.Process(pid)
        self.monitoring = True
        self.cpu_usage = []
        self.memory_usage = []
        self.timestamps = []
        
        def monitor():
            start_time = time.time()
            while self.monitoring:
                try:
                    cpu = self.process.cpu_percent()
                    memory = self.process.memory_info().rss / 1024 / 1024  # MB
                    timestamp = time.time() - start_time
                    
                    self.cpu_usage.append(cpu)
                    self.memory_usage.append(memory)
                    self.timestamps.append(timestamp)
                    
                    time.sleep(0.5)  # 0.5秒采样一次
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
        
        self.monitor_thread = threading.Thread(target=monitor)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        return {
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'timestamps': self.timestamps,
            'avg_cpu': sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0,
            'max_memory': max(self.memory_usage) if self.memory_usage else 0,
            'avg_memory': sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0
        }

class ServerTester:
    def __init__(self, script_path: str, server_name: str, port: int = 8001):
        self.script_path = script_path
        self.server_name = server_name
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self.process = None
        self.monitor = PerformanceMonitor()
        
    def start_server(self) -> Dict:
        """启动服务器并测量启动时间"""
        print(f"\n🚀 启动 {self.server_name} 服务器...")
        start_time = time.time()
        
        # 启动服务器进程
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(self.script_path).parent)
        
        self.process = subprocess.Popen(
            [sys.executable, self.script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=env,
            cwd=Path(self.script_path).parent
        )
        
        # 开始性能监控
        self.monitor.start_monitoring(self.process.pid)
        
        # 等待服务器启动
        model_load_time = None
        startup_complete = False
        
        while True:
            line = self.process.stdout.readline()
            if not line:
                break
                
            print(f"[{self.server_name}] {line.strip()}")
            
            # 检测模型加载完成
            if "模型加载完成" in line and "耗时" in line:
                # 提取加载时间
                import re
                match = re.search(r'耗时: ([\d.]+) 秒', line)
                if match:
                    model_load_time = float(match.group(1))
            
            # 检测服务器启动完成
            if "Uvicorn running on" in line:
                startup_time = time.time() - start_time
                startup_complete = True
                break
                
            # 检查进程是否异常退出
            if self.process.poll() is not None:
                print(f"❌ {self.server_name} 服务器启动失败!")
                return None
        
        if not startup_complete:
            print(f"❌ {self.server_name} 服务器启动超时!")
            return None
        
        # 等待服务器完全就绪
        self._wait_for_health_check()
        
        total_startup_time = time.time() - start_time
        
        return {
            'startup_time': total_startup_time,
            'model_load_time': model_load_time,
            'server_ready': True
        }
    
    def _wait_for_health_check(self, timeout: int = 30):
        """等待服务器健康检查通过"""
        print(f"⏳ 等待 {self.server_name} 服务器就绪...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/", timeout=5)
                if response.status_code == 200:
                    print(f"✅ {self.server_name} 服务器就绪!")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        raise Exception(f"{self.server_name} 服务器健康检查失败!")
    
    def test_inference(self, audio_file: str, num_tests: int = 5) -> Dict:
        """测试推理性能"""
        print(f"\n🧪 测试 {self.server_name} 推理性能 (共{num_tests}次)...")
        
        if not Path(audio_file).exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")
        
        results = []
        
        for i in range(num_tests):
            print(f"  测试 {i+1}/{num_tests}...")
            start_time = time.time()
            
            try:
                with open(audio_file, 'rb') as f:
                    files = {'file': f}
                    data = {'language': 'auto', 'use_itn': True}
                    
                    response = requests.post(
                        f"{self.base_url}/transcribe/normal",
                        files=files,
                        data=data,
                        timeout=60
                    )
                
                inference_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    results.append({
                        'inference_time': inference_time,
                        'text': result.get('text', ''),
                        'success': True
                    })
                    print(f"    ✅ 耗时: {inference_time:.2f}s")
                    print(f"    📝 结果: {result.get('text', '')[:50]}...")
                else:
                    results.append({
                        'inference_time': inference_time,
                        'text': '',
                        'success': False,
                        'error': response.text
                    })
                    print(f"    ❌ 请求失败: {response.status_code}")
                    
            except Exception as e:
                results.append({
                    'inference_time': time.time() - start_time,
                    'text': '',
                    'success': False,
                    'error': str(e)
                })
                print(f"    ❌ 异常: {e}")
        
        # 计算统计信息
        successful_results = [r for r in results if r['success']]
        if successful_results:
            inference_times = [r['inference_time'] for r in successful_results]
            return {
                'total_tests': num_tests,
                'successful_tests': len(successful_results),
                'first_inference_time': results[0]['inference_time'] if results[0]['success'] else None,
                'avg_inference_time': sum(inference_times) / len(inference_times),
                'min_inference_time': min(inference_times),
                'max_inference_time': max(inference_times),
                'all_results': results
            }
        else:
            return {
                'total_tests': num_tests,
                'successful_tests': 0,
                'error': 'All tests failed',
                'all_results': results
            }
    
    def stop_server(self) -> Dict:
        """停止服务器并获取性能数据"""
        print(f"\n🛑 停止 {self.server_name} 服务器...")
        
        # 停止性能监控
        perf_data = self.monitor.stop_monitoring()
        
        # 终止服务器进程
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        
        return perf_data

class PerformanceComparison:
    def __init__(self, audio_file: str):
        self.audio_file = audio_file
        self.results = {}
        
        # 配置测试服务器
        self.servers = {
            'ONNX': ServerTester(
                '/Users/yangdongju/Desktop/code_project/pc/Ohoo/python-service/server.py',
                'ONNX (优化模型)'
            ),
             'PyTorch': ServerTester(
                '/Users/yangdongju/Desktop/code_project/pc/Ohoo/python-service/server_torch.py',
                'PyTorch (.pt模型)'
            )
        }
    
    def run_comparison(self, num_inference_tests: int = 5):
        """运行完整的性能对比测试"""
        print("=" * 60)
        print("🏁 SenseVoice 性能对比测试开始")
        print("=" * 60)
        
        for server_type, tester in self.servers.items():
            print(f"\n{'='*20} {server_type} 测试 {'='*20}")
            
            try:
                # 1. 测试启动性能
                startup_result = tester.start_server()
                if not startup_result:
                    print(f"❌ {server_type} 启动失败，跳过测试")
                    continue
                
                # 2. 测试推理性能
                inference_result = tester.test_inference(self.audio_file, num_inference_tests)
                
                # 3. 获取性能监控数据
                perf_data = tester.stop_server()
                
                # 保存结果
                self.results[server_type] = {
                    'startup': startup_result,
                    'inference': inference_result,
                    'performance': perf_data
                }
                
                print(f"✅ {server_type} 测试完成")
                
            except Exception as e:
                print(f"❌ {server_type} 测试失败: {e}")
                tester.stop_server()
                continue
            
            # 等待一下再测试下一个
            time.sleep(3)
    
    def generate_report(self):
        """生成性能对比报告"""
        if not self.results:
            print("❌ 没有可用的测试结果")
            return
        
        print("\n" + "="*60)
        print("📊 性能对比报告")
        print("="*60)
        
        # 创建对比表格
        comparison_data = []
        
        for server_type, data in self.results.items():
            startup = data.get('startup', {})
            inference = data.get('inference', {})
            performance = data.get('performance', {})
            
            comparison_data.append({
                '模型类型': server_type,
                '启动时间(s)': f"{startup.get('startup_time', 0):.2f}",
                '模型加载时间(s)': f"{startup.get('model_load_time', 0):.2f}",
                '首次推理时间(s)': f"{inference.get('first_inference_time', 0):.2f}",
                '平均推理时间(s)': f"{inference.get('avg_inference_time', 0):.2f}",
                '最快推理时间(s)': f"{inference.get('min_inference_time', 0):.2f}",
                '平均内存使用(MB)': f"{performance.get('avg_memory', 0):.0f}",
                '峰值内存使用(MB)': f"{performance.get('max_memory', 0):.0f}",
                '平均CPU使用(%)': f"{performance.get('avg_cpu', 0):.1f}%"
            })
        
        # 显示对比表格
        df = pd.DataFrame(comparison_data)
        print("\n📋 详细对比数据:")
        print(df.to_string(index=False))
        
        # 计算性能提升
        if 'PyTorch' in self.results and 'ONNX' in self.results:
            pytorch_data = self.results['PyTorch']
            onnx_data = self.results['ONNX']
            
            print("\n🚀 ONNX vs PyTorch 性能提升:")
            
            # 启动时间提升
            pytorch_startup = pytorch_data['startup'].get('startup_time', 0)
            onnx_startup = onnx_data['startup'].get('startup_time', 0)
            if pytorch_startup > 0:
                startup_improvement = ((pytorch_startup - onnx_startup) / pytorch_startup) * 100
                print(f"  • 启动速度提升: {startup_improvement:.1f}%")
            
            # 推理时间提升
            pytorch_inference = pytorch_data['inference'].get('avg_inference_time', 0)
            onnx_inference = onnx_data['inference'].get('avg_inference_time', 0)
            if pytorch_inference > 0:
                inference_improvement = ((pytorch_inference - onnx_inference) / pytorch_inference) * 100
                print(f"  • 推理速度提升: {inference_improvement:.1f}%")
            
            # 内存使用对比
            pytorch_memory = pytorch_data['performance'].get('avg_memory', 0)
            onnx_memory = onnx_data['performance'].get('avg_memory', 0)
            if pytorch_memory > 0:
                memory_reduction = ((pytorch_memory - onnx_memory) / pytorch_memory) * 100
                print(f"  • 内存使用减少: {memory_reduction:.1f}%")
        
        # 保存详细结果到文件
        self.save_results()
    
    def save_results(self):
        """保存测试结果到文件"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        results_file = f"performance_test_results_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 详细结果已保存到: {results_file}")
    
    def create_visualizations(self):
        """创建性能对比可视化图表"""
        if len(self.results) < 2:
            return
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('SenseVoice 性能对比', fontsize=16)
        
        # 1. 启动时间对比
        startup_times = []
        labels = []
        for server_type, data in self.results.items():
            startup_time = data['startup'].get('startup_time', 0)
            startup_times.append(startup_time)
            labels.append(server_type)
        
        axes[0, 0].bar(labels, startup_times, color=['#ff7f0e', '#2ca02c'])
        axes[0, 0].set_title('启动时间对比')
        axes[0, 0].set_ylabel('时间 (秒)')
        for i, v in enumerate(startup_times):
            axes[0, 0].text(i, v + 0.1, f'{v:.2f}s', ha='center')
        
        # 2. 推理时间对比
        inference_times = []
        for server_type, data in self.results.items():
            inference_time = data['inference'].get('avg_inference_time', 0)
            inference_times.append(inference_time)
        
        axes[0, 1].bar(labels, inference_times, color=['#ff7f0e', '#2ca02c'])
        axes[0, 1].set_title('平均推理时间对比')
        axes[0, 1].set_ylabel('时间 (秒)')
        for i, v in enumerate(inference_times):
            axes[0, 1].text(i, v + 0.01, f'{v:.3f}s', ha='center')
        
        # 3. 内存使用对比
        memory_usage = []
        for server_type, data in self.results.items():
            memory = data['performance'].get('avg_memory', 0)
            memory_usage.append(memory)
        
        axes[1, 0].bar(labels, memory_usage, color=['#ff7f0e', '#2ca02c'])
        axes[1, 0].set_title('平均内存使用对比')
        axes[1, 0].set_ylabel('内存 (MB)')
        for i, v in enumerate(memory_usage):
            axes[1, 0].text(i, v + 10, f'{v:.0f}MB', ha='center')
        
        # 4. 性能监控时间序列（如果有数据）
        if 'ONNX' in self.results and self.results['ONNX']['performance']['timestamps']:
            onnx_perf = self.results['ONNX']['performance']
            axes[1, 1].plot(onnx_perf['timestamps'], onnx_perf['memory_usage'], 
                           label='ONNX内存', color='#2ca02c')
            
            if 'PyTorch' in self.results and self.results['PyTorch']['performance']['timestamps']:
                pytorch_perf = self.results['PyTorch']['performance']
                axes[1, 1].plot(pytorch_perf['timestamps'], pytorch_perf['memory_usage'], 
                               label='PyTorch内存', color='#ff7f0e')
            
            axes[1, 1].set_title('运行时内存使用')
            axes[1, 1].set_xlabel('时间 (秒)')
            axes[1, 1].set_ylabel('内存 (MB)')
            axes[1, 1].legend()
        
        plt.tight_layout()
        
        # 保存图表
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        chart_file = f"performance_comparison_{timestamp}.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        print(f"📊 性能对比图表已保存到: {chart_file}")
        
        # 显示图表
        plt.show()

def main():
    """主函数"""
    audio_file = "/Users/yangdongju/Downloads/录音记录_20250928_0006.wav"
    
    if not Path(audio_file).exists():
        print(f"❌ 音频文件不存在: {audio_file}")
        return
    
    print("🎯 SenseVoice 性能对比测试工具")
    print(f"🎵 测试音频: {audio_file}")
    
    # 创建性能对比测试
    comparison = PerformanceComparison(audio_file)
    
    # 运行测试
    comparison.run_comparison(num_inference_tests=5)
    
    # 生成报告
    comparison.generate_report()
    
    # 创建可视化图表
    try:
        comparison.create_visualizations()
    except ImportError:
        print("⚠️ matplotlib 未安装，跳过图表生成")
    except Exception as e:
        print(f"⚠️ 图表生成失败: {e}")

if __name__ == "__main__":
    main()