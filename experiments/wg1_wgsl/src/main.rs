use std::time::Instant;
use wgpu::util::DeviceExt;

const SHADER: &str = r#"
struct Sim { n: u32, pad: vec3<u32> };
@group(0) @binding(0) var<storage, read> input : array<f32>;
@group(0) @binding(1) var<storage, read_write> output : array<f32>;
@group(0) @binding(2) var<uniform> sim : Sim;

var<workgroup> tile : array<f32, 64u>;

// A: workgroup-memory ring tick — threads read NEIGHBORS' slots (real reuse)
@compute @workgroup_size(64, 1, 1)
fn shared_tick(@builtin(global_invocation_id) gid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    let g = gid.x; let l = lid.x; let n = sim.n;
    tile[l] = input[g];
    workgroupBarrier();
    // halo: interior neighbours come from shared memory, only the 2 edge threads touch global
    let left  = select(tile[(l + 63u) & 63u], input[(g + n - 1u) % n], l == 0u);
    let right = select(tile[(l + 1u) & 63u],   input[(g + 1u) % n],     l == 63u);
    output[g] = 3.0 * tile[l] - left - right;
}

// B: same math, neighbors straight from global memory (no shared mem)
@compute @workgroup_size(64, 1, 1)
fn direct_tick(@builtin(global_invocation_id) gid: vec3<u32>) {
    let g = gid.x; let n = sim.n;
    let v = input[g];
    let left  = input[(g + n - 1u) % n];
    let right = input[(g + 1u) % n];
    output[g] = 3.0 * v - left - right;
}

// C: the 1:1 template — shared memory roundtrip, zero reuse
@compute @workgroup_size(64, 1, 1)
fn casey_pass(@builtin(global_invocation_id) gid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    let g = gid.x; let l = lid.x;
    tile[l] = input[g];
    workgroupBarrier();
    output[g] = tile[l] + 1.0;
}

// D: pure registers — the floor to compare C against
@compute @workgroup_size(64, 1, 1)
fn pure_copy(@builtin(global_invocation_id) gid: vec3<u32>) {
    output[gid.x] = input[gid.x] + 1.0;
}
"#;

fn main() { pollster::block_on(run()); }

async fn run() {
    let n: u32 = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(1 << 20);
    let iters: u32 = std::env::args().nth(2).and_then(|s| s.parse().ok()).unwrap_or(200);
    let groups = n / 64;
    let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor::default());
    let adapter = instance.request_adapter(&wgpu::RequestAdapterOptions {
        power_preference: wgpu::PowerPreference::HighPerformance,
        compatible_surface: None, force_fallback_adapter: false,
    }).await.expect("no adapter");
    let info = adapter.get_info();
    println!("ADAPTER: {} | backend {:?} | driver {}", info.name, info.backend, info.driver);
    let (device, queue) = adapter.request_device(&wgpu::DeviceDescriptor {
        label: None, required_features: wgpu::Features::empty(),
        required_limits: wgpu::Limits::default(), ..Default::default()
    }, None).await.unwrap();
    let lim = device.limits();
    println!("LIMITS: wg_storage={}B wg_x={} invocations={}", lim.max_compute_workgroup_storage_size, lim.max_compute_workgroup_size_x, lim.max_compute_invocations_per_workgroup);

    let src: Vec<f32> = (0..n).map(|i| ((i as u64 * 2654435761u64) % 1000) as f32 / 100.0).collect();
    let src_buf = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("src"), contents: bytemuck::cast_slice(&src),
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC });
    let dst_buf = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("dst"), size: (n as u64) * 4, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false });
    let sim_buf = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("sim"), contents: bytemuck::cast_slice(&[n, 0u32, 0, 0, 0, 0, 0, 0]),
        usage: wgpu::BufferUsages::UNIFORM });
    let module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("wg1"), source: wgpu::ShaderSource::Wgsl(std::borrow::Cow::Borrowed(SHADER)) });
    let bgl = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
        label: Some("bgl"),
        entries: &[
            wgpu::BindGroupLayoutEntry { binding: 0, visibility: wgpu::ShaderStages::COMPUTE,
                ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: true }, has_dynamic_offset: false, min_binding_size: None }, count: None },
            wgpu::BindGroupLayoutEntry { binding: 1, visibility: wgpu::ShaderStages::COMPUTE,
                ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
            wgpu::BindGroupLayoutEntry { binding: 2, visibility: wgpu::ShaderStages::COMPUTE,
                ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Uniform, has_dynamic_offset: false, min_binding_size: None }, count: None },
        ] });
    let pl = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: None, bind_group_layouts: &[&bgl], push_constant_ranges: &[] });
    let names = ["shared_tick", "direct_tick", "casey_pass", "pure_copy"];
    let pipes: Vec<(&str, wgpu::ComputePipeline)> = names.iter().map(|name| (*name,
        device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some(name), layout: Some(&pl), module: &module,
            entry_point: Some(name), compilation_options: Default::default(), cache: None }))).collect();
    let bg = device.create_bind_group(&wgpu::BindGroupDescriptor {
        layout: &bgl,
        entries: &[
            wgpu::BindGroupEntry { binding: 0, resource: src_buf.as_entire_binding() },
            wgpu::BindGroupEntry { binding: 1, resource: dst_buf.as_entire_binding() },
            wgpu::BindGroupEntry { binding: 2, resource: sim_buf.as_entire_binding() }],
        label: Some("bg") });
    for (name, pipe) in &pipes {
        let name = *name;
        // timing pass
        let mut enc = device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        { let mut p = enc.begin_compute_pass(&wgpu::ComputePassDescriptor { label: None, timestamp_writes: None });
          p.set_pipeline(pipe); p.set_bind_group(0, &bg, &[]);
          for _ in 0..iters { p.dispatch_workgroups(groups, 1, 1); } }
        let t0 = Instant::now();
        queue.submit(Some(enc.finish())); device.poll(wgpu::Maintain::Wait);
        let dt = t0.elapsed().as_secs_f64();
        println!("KERN {}: {:>8.2} ms total | {:>7.3} us/dispatch | {:>10.1} Mnodes/s", name, dt * 1e3, dt * 1e6 / iters as f64, (n as f64) * iters as f64 / dt / 1e6);
        // golden readback (one dispatch)
        let mut enc = device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        { let mut p = enc.begin_compute_pass(&wgpu::ComputePassDescriptor { label: None, timestamp_writes: None });
          p.set_pipeline(pipe); p.set_bind_group(0, &bg, &[]); p.dispatch_workgroups(groups, 1, 1); }
        let rb = device.create_buffer(&wgpu::BufferDescriptor { label: Some("rb"), size: (n as u64) * 4, usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ, mapped_at_creation: false });
        enc.copy_buffer_to_buffer(&dst_buf, 0, &rb, 0, (n as u64) * 4);
        queue.submit(Some(enc.finish()));
        let (tx, rx) = std::sync::mpsc::channel();
        rb.slice(..).map_async(wgpu::MapMode::Read, move |r| tx.send(r).unwrap());
        device.poll(wgpu::Maintain::Wait); rx.recv().unwrap().unwrap();
        let got: Vec<f32> = bytemuck::cast_slice(&rb.slice(..).get_mapped_range()).to_vec();
        rb.unmap();
        let expect: Vec<f32> = match name {
            "shared_tick" | "direct_tick" => (0..n).map(|i| 3.0 * src[i as usize] - src[((i + n - 1) % n) as usize] - src[((i + 1) % n) as usize]).collect(),
            _ => src.iter().map(|v| v + 1.0).collect() };
        let bad = expect.iter().zip(got.iter()).filter(|(a, b)| ((**a - **b) / (**a).abs().max(1e-9)).abs() > 1e-4).count();
        println!("  GOLDEN {} ({})", if bad == 0 { "PASS" } else { "FAIL" }, bad);
    }
}
