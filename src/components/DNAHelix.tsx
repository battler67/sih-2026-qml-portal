import { Canvas, useFrame } from "@react-three/fiber";
import { Float, Environment } from "@react-three/drei";
import { useMemo, useRef, Suspense } from "react";
import * as THREE from "three";

const BASE_COLORS: Record<string, string> = {
  A: "#10B981",
  T: "#ef4444",
  G: "#eab308",
  C: "#38bdf8",
};

function HelixStrand({ mouse }: { mouse: React.MutableRefObject<{ x: number; y: number }> }) {
  const group = useRef<THREE.Group>(null!);
  const nucleotides = useMemo(() => {
    const arr: { pos: THREE.Vector3; base: string; side: number; t: number }[] = [];
    const count = 40;
    const bases = ["A", "T", "G", "C"];
    for (let i = 0; i < count; i++) {
      const t = i / count;
      const y = (i - count / 2) * 0.35;
      const angle = t * Math.PI * 8;
      const r = 1.2;
      arr.push({
        pos: new THREE.Vector3(Math.cos(angle) * r, y, Math.sin(angle) * r),
        base: bases[i % 4],
        side: 1,
        t,
      });
      arr.push({
        pos: new THREE.Vector3(Math.cos(angle + Math.PI) * r, y, Math.sin(angle + Math.PI) * r),
        base: bases[(i + 2) % 4],
        side: -1,
        t,
      });
    }
    return arr;
  }, []);

  const rungs = useMemo(() => {
    const rungs: { a: THREE.Vector3; b: THREE.Vector3 }[] = [];
    for (let i = 0; i < nucleotides.length; i += 2) {
      rungs.push({ a: nucleotides[i].pos, b: nucleotides[i + 1].pos });
    }
    return rungs;
  }, [nucleotides]);

  const inner = useRef<THREE.Group>(null!);

  useFrame((_, delta) => {
    if (!inner.current || !group.current) return;
    // Spin around the strand's own central (Y) axis
    inner.current.rotation.y += delta * 0.6;
    // Mouse parallax: subtle viewing-angle shift on the outer (tilted) group
    const targetX = mouse.current.y * 0.25;
    const targetY = mouse.current.x * 0.35;
    group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, targetX, 0.05);
    // Base tilt: diagonal bottom-left -> top-right (rotate around Z), plus parallax yaw
    group.current.rotation.z = THREE.MathUtils.lerp(group.current.rotation.z, -Math.PI / 4, 0.05);
    group.current.position.x = THREE.MathUtils.lerp(group.current.position.x, targetY * 0.2, 0.05);
  });

  return (
    <group ref={group}>
      <group ref={inner}>
        {nucleotides.map((n, i) => (
          <mesh key={i} position={n.pos}>
            <sphereGeometry args={[0.18, 24, 24]} />
            <meshStandardMaterial
              color={BASE_COLORS[n.base]}
              emissive={BASE_COLORS[n.base]}
              emissiveIntensity={0.9}
              roughness={0.25}
              metalness={0.4}
            />
          </mesh>
        ))}
        {rungs.map((r, i) => {
          const mid = r.a.clone().add(r.b).multiplyScalar(0.5);
          const dir = r.b.clone().sub(r.a);
          const len = dir.length();
          const quat = new THREE.Quaternion().setFromUnitVectors(
            new THREE.Vector3(0, 1, 0),
            dir.clone().normalize(),
          );
          return (
            <mesh key={`r${i}`} position={mid} quaternion={quat}>
              <cylinderGeometry args={[0.04, 0.04, len, 8]} />
              <meshStandardMaterial
                color="#10B981"
                emissive="#10B981"
                emissiveIntensity={0.6}
                transparent
                opacity={0.6}
              />
            </mesh>
          );
        })}
        {/* backbone tubes */}
        <BackboneTube offset={0} />
        <BackboneTube offset={Math.PI} />
      </group>
    </group>
  );
}

function BackboneTube({ offset }: { offset: number }) {
  const curve = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 200; i++) {
      const t = i / 200;
      const y = (t - 0.5) * 14;
      const angle = t * Math.PI * 8 + offset;
      pts.push(new THREE.Vector3(Math.cos(angle) * 1.2, y, Math.sin(angle) * 1.2));
    }
    return new THREE.CatmullRomCurve3(pts);
  }, [offset]);
  return (
    <mesh>
      <tubeGeometry args={[curve, 300, 0.06, 12, false]} />
      <meshStandardMaterial
        color="#34d399"
        emissive="#10B981"
        emissiveIntensity={0.9}
        roughness={0.2}
        metalness={0.6}
      />
    </mesh>
  );
}

function Particles() {
  const ref = useRef<THREE.Points>(null!);
  const { positions, colors } = useMemo(() => {
    const n = 400;
    const positions = new Float32Array(n * 3);
    const colors = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 20;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 20;
      const c = new THREE.Color(Math.random() > 0.5 ? "#10B981" : "#38bdf8");
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
    return { positions, colors };
  }, []);
  useFrame((_, d) => {
    if (ref.current) ref.current.rotation.y += d * 0.02;
  });
  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.06}
        vertexColors
        transparent
        opacity={0.8}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

export function DNAHelix({ className = "" }: { className?: string }) {
  const mouse = useRef({ x: 0, y: 0 });
  return (
    <div
      className={className}
      onMouseMove={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        mouse.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.current.y = ((e.clientY - rect.top) / rect.height) * 2 - 1;
      }}
    >
      <Canvas
        camera={{ position: [0, 0, 8], fov: 45 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
      >
        <Suspense fallback={null}>
          <color attach="background" args={["#000000"]} />
          <fog attach="fog" args={["#04120c", 8, 22]} />
          <ambientLight intensity={0.3} />
          <pointLight position={[5, 5, 5]} intensity={2} color="#10B981" />
          <pointLight position={[-5, -5, -5]} intensity={1.5} color="#38bdf8" />
          <HelixStrand mouse={mouse} />
          <Particles />
          <Environment preset="night" />
        </Suspense>
      </Canvas>
    </div>
  );
}
