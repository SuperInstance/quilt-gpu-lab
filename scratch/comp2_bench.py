import time, subprocess, torch, torch.nn as nn
dev = torch.device("cuda")
NSMI="/usr/lib/wsl/lib/nvidia-smi"
def pw():
    try:
        o=subprocess.run([NSMI,"--query-gpu=power.draw,utilization.gpu","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=10).stdout.splitlines()[0]
        p,u=[x.strip() for x in o.split(",")]; return float(p),float(u)
    except Exception: return None,None
def net(h): return nn.Sequential(nn.Linear(64,h),nn.Tanh(),nn.Linear(h,1)).to(dev)
torch.manual_seed(2718)
X=torch.randn(4096,64,device=dev); Y=(torch.rand(4096,device=dev)>0.5).float()
# ramp
a=torch.randn(2048,2048,device=dev); t0=time.time()
while time.time()-t0<0.6: a=a@a; a/=a.norm()
torch.cuda.synchronize()
for h,batch,nup in [(64,16,20000),(64,16,20000),(16,16,40000),(64,128,20000)]:
    m=net(h); opt=torch.optim.Adam(m.parameters(),lr=1e-3); lf=nn.BCEWithLogitsLoss()
    ps=[]
    t0=time.time()
    done=0
    while done<nup:
        idx=torch.randint(0,4096,(batch,),device=dev)
        opt.zero_grad(); loss=lf(m(X[idx]).squeeze(-1),Y[idx]); loss.backward(); opt.step()
        done+=batch
        if done%2000==0:
            p,u=pw(); ps.append(p)
    torch.cuda.synchronize()
    wall=time.time()-t0
    pp=[p for p in ps if p]
    meanp=sum(pp)/len(pp) if pp else 0
    ups=done/wall
    print(f"h={h} B={batch}: {done} upd in {wall:.2f}s = {ups:.0f} upd/s  meanP={meanp:.1f}W  -> Wh per 1e6 upd = {meanp/ups*1e6/3600:.3f}", flush=True)
