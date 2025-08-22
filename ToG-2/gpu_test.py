import torch

def check_cuda():
    if torch.cuda.is_available():
        print("✅ CUDA is available!")
        print("Number of GPUs:", torch.cuda.device_count())
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
    else:
        print("❌ CUDA is NOT available.")

if __name__ == "__main__":
    check_cuda()
