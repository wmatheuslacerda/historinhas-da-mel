import {Easing, Img, interpolate, random, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {camadas, intensidade, olhos, Voz} from './dados';

export type Anim = {
  respira?: number; // amplitude da respiração
  periodo?: number; // segundos por respiração
  balanco?: number; // graus de balanço lento
  tremor?: number; // px de tremedeira (medo)
  fala?: Voz[]; // quica quando essa voz fala
  falaAmp?: number;
  soVertical?: boolean; // não gira ao falar (quando encosta em algo fixo)
  inclinaQuando?: {voz: Voz; graus: number}; // inclina quando o outro fala
  entrada?: {dx: number; dy: number; inicio: number}; // desliza para dentro (quadro local)
  saida?: {dx: number; dy: number; inicio: number; dur: number};
  risada?: {ini: number; fim: number; amp: number}[]; // quadros locais
  soluco?: boolean;
  piscar?: boolean;
  seed?: number;
};

type Props = {
  nome: string;
  pivo: [number, number]; // ponto de apoio (pés/assento) em coordenadas do palco
  anim: Anim;
  inicioGlobal: number; // quadro global em que a Sequence começa
  sombra?: {x: number; y: number; w: number; h: number; o?: number};
};

const FECHA = [0.35, 0.75, 1, 1, 0.85, 0.55, 0.25, 0.05];

const piscadas = (seed: number) => {
  const lista: number[] = [];
  let k = Math.floor(18 + random(`p${seed}`) * 40);
  let i = 0;
  while (k < 2000) {
    lista.push(k);
    i++;
    k += Math.floor(78 + random(`p${seed}-${i}`) * 60);
  }
  return lista;
};

const escurecer = (hex: string, f: number) => {
  const n = parseInt(hex.slice(1), 16);
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => Math.round(v * f));
  return `rgb(${c.join(',')})`;
};

export const Personagem: React.FC<Props> = ({nome, pivo, anim, inicioGlobal, sombra}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const g = inicioGlobal + f;
  const t = f / fps;
  const seed = anim.seed ?? 0;
  const L = camadas[nome];

  const resp = anim.respira ?? 0.012;
  const b = Math.sin((2 * Math.PI * t) / (anim.periodo ?? 3.4) + seed);
  let sx = 1 - resp * 0.4 * b;
  let sy = 1 + resp * b;
  let rot = (anim.balanco ?? 0.5) * Math.sin((2 * Math.PI * t) / 4.7 + seed * 2);
  let tx = 0;
  let ty = 0;

  if (anim.tremor) {
    tx += (anim.tremor * (Math.sin(f * 1.7) + Math.sin(f * 2.9 + 1))) / 2;
    ty += anim.tremor * 0.5 * Math.sin(f * 2.3 + 2);
  }

  for (const v of anim.fala ?? []) {
    const e = intensidade(v, g);
    ty -= e * (anim.falaAmp ?? 14);
    sy += e * 0.02;
    sx -= e * 0.006;
    if (!anim.soVertical) rot += e * 1.4 * Math.sin(f * 0.55);
  }

  if (anim.inclinaQuando) {
    const e = intensidade(anim.inclinaQuando.voz, g);
    rot += anim.inclinaQuando.graus * Math.min(1, e * 1.5);
  }

  for (const r of anim.risada ?? []) {
    const a =
      interpolate(f, [r.ini - 6, r.ini, r.fim, r.fim + 12], [0, 1, 1, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      }) * r.amp;
    const pulo = Math.abs(Math.sin((2 * Math.PI * f) / 9));
    ty -= a * 20 * pulo;
    sy += a * 0.028 * (pulo - 0.5);
    sx -= a * 0.012 * (pulo - 0.5);
    rot += a * 1.6 * Math.sin((2 * Math.PI * f) / 18);
  }

  if (anim.soluco) {
    const ph = t % 1.8;
    const s =
      ph < 0.28 ? Math.sin((ph / 0.28) * Math.PI) : ph > 0.45 && ph < 0.72 ? 0.7 * Math.sin(((ph - 0.45) / 0.27) * Math.PI) : 0;
    ty -= s * 7;
    sy += s * 0.014;
  }

  if (anim.entrada) {
    const p = spring({frame: f - anim.entrada.inicio, fps, config: {damping: 12, stiffness: 60, mass: 1}});
    tx += anim.entrada.dx * (1 - p);
    ty += anim.entrada.dy * (1 - p) - Math.abs(Math.sin(f * 0.9)) * 10 * (1 - p);
    rot += (1 - p) * (anim.entrada.dx < 0 ? 7 : -7);
    sx += (1 - p) * 0.04;
  }

  if (anim.saida) {
    const q = interpolate(f, [anim.saida.inicio, anim.saida.inicio + anim.saida.dur], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.in(Easing.cubic),
    });
    tx += anim.saida.dx * q;
    ty += anim.saida.dy * q - Math.abs(Math.sin(f * 0.9)) * 8 * q;
    rot += q * (anim.saida.dx > 0 ? 6 : -6);
  }

  const ox = pivo[0] - L.x;
  const oy = pivo[1] - L.y;

  // pálpebras
  const lista = anim.piscar ? piscadas(seed) : [];
  let c = 0;
  for (const s of lista) {
    const d = f - s;
    if (d >= 0 && d < FECHA.length) c = FECHA[d];
  }
  const meusOlhos = anim.piscar ? olhos[nome] ?? [] : [];

  return (
    <>
      {sombra ? (
        <div
          style={{
            position: 'absolute',
            left: sombra.x - sombra.w / 2,
            top: sombra.y - sombra.h / 2,
            width: sombra.w,
            height: sombra.h,
            borderRadius: '50%',
            background: `radial-gradient(ellipse at center, rgba(30,15,10,${sombra.o ?? 0.38}) 0%, rgba(30,15,10,0) 70%)`,
            transform: `translateX(${tx}px) scaleX(${1 + Math.min(0, ty) / 300})`,
          }}
        />
      ) : null}
      <div
        style={{
          position: 'absolute',
          left: L.x,
          top: L.y,
          width: L.w,
          height: L.h,
          transformOrigin: `${ox}px ${oy}px`,
          transform: `translate(${tx}px, ${ty}px) rotate(${rot}deg) scale(${sx}, ${sy})`,
        }}
      >
        <Img src={staticFile(`camadas/${nome}.png`)} style={{width: '100%', height: '100%'}} />
        {c > 0 && meusOlhos.length ? (
          <svg width={L.w} height={L.h} style={{position: 'absolute', left: 0, top: 0}}>
            {meusOlhos.map((o, i) => {
              const cx = o.cx - L.x;
              const cy = o.cy - L.y;
              const R = {rx: o.rx * 1.2, ry: o.ry * 1.28};
              const topo = cy - R.ry;
              const h = 2 * R.ry * c + 1;
              const ly = Math.min(topo + h, cy + o.ry * 0.3);
              const id = `olho-${nome}-${i}`;
              return (
                <g key={i}>
                  <defs>
                    <clipPath id={id}>
                      <ellipse cx={cx} cy={cy} rx={R.rx} ry={R.ry} />
                    </clipPath>
                    <linearGradient id={`${id}-g`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0" stopColor={escurecer(o.pele, 0.95)} />
                      <stop offset="1" stopColor={escurecer(o.pele, 0.82)} />
                    </linearGradient>
                  </defs>
                  <g clipPath={`url(#${id})`}>
                    <rect x={cx - R.rx} y={topo} width={2 * R.rx} height={h} fill={`url(#${id}-g)`} />
                  </g>
                  <path
                    d={`M ${cx - R.rx * 0.95} ${ly} Q ${cx} ${ly + o.ry * 0.38 * c} ${cx + R.rx * 0.95} ${ly}`}
                    stroke="#2b1710"
                    strokeWidth={3.2}
                    strokeLinecap="round"
                    fill="none"
                    opacity={c > 0.25 ? 1 : c / 0.25}
                  />
                </g>
              );
            })}
          </svg>
        ) : null}
      </div>
    </>
  );
};
