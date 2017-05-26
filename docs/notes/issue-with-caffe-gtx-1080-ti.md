When I run caffe training on gtx 1080 ti card, it shows the following error:

```
I0505 18:55:23.179957     7 caffe.cpp:223] GPU 0: Graphics Device
E0505 18:55:23.231144     7 common.cpp:114] Cannot create Cublas handle. Cublas won't be available.
E0505 18:55:23.308081     7 common.cpp:121] Cannot create Curand generator. Curand won't be available.
F0505 18:55:23.356746     7 benchmark.cpp:112] Check failed: error == cudaSuccess (46 vs. 0)  all CUDA-capable devices are busy or unavailable
*** Check failure stack trace: ***
    @     0x7f536d5cb5cd  google::LogMessage::Fail()
    @     0x7f536d5cd433  google::LogMessage::SendToLog()
    @     0x7f536d5cb15b  google::LogMessage::Flush()
    @     0x7f536d5cde1e  google::LogMessageFatal::~LogMessageFatal()
    @     0x7f536dba868c  caffe::Timer::Init()
    @     0x7f536db513c4  caffe::Solver<>::Solver()
    @     0x7f536db34d51  caffe::Creator_SGDSolver<>()
    @           0x416dac  caffe::SolverRegistry<>::CreateSolver()
    @           0x40e67d  train()
    @           0x40b8a3  main
    @     0x7f536c2b8830  __libc_start_main
    @           0x40c249  _start
    @              (nil)  (unknown)
/job/launch-921fb858-fbe6-4dc9-8b71-0012f0a6092f.sh: line 1:     7 Aborted                 (core dumped) caffe train -solver /work/caffe/solver_resnet18.prototxt

```

The same job can be run as root or use sudo. 
Interesting thing is that after I run as root or sudo, the same job can be run by regular user. 
I guess caffe is trying to create "Cublas handle" and "Curand generator" by root permission, which doesn't make sense. 
More investigations are need to solve this permission issue. 


the same settings works find with other GPU type, e.g. titan X, M40. 
