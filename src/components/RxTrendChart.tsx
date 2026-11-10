import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { monthLabels } from '../lib/format';

interface Props {
  history: number[];
  trendWindow?: number;
}

export function RxTrendChart({ history, trendWindow = 3 }: Props) {
  const labels = monthLabels(history.length);
  const data = history.map((rx, i) => ({ month: labels[i], rx }));
  const windowStart = labels[labels.length - 1 - trendWindow];

  return (
    <figure className="chart">
      <figcaption className="chart__caption">
        Monthly prescriptions, last {history.length} months
        <span className="chart__legend">Shaded: {trendWindow}-month trend window</span>
      </figcaption>
      <div className="chart__canvas" role="img" aria-label={`Prescriptions by month: ${data.map((d) => `${d.month} ${d.rx}`).join(', ')}`}>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
            <defs>
              <linearGradient id="rxFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--cobalt-700)" stopOpacity={0.28} />
                <stop offset="100%" stopColor="var(--cobalt-700)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            <ReferenceArea x1={windowStart} x2={labels[labels.length - 1]} fill="var(--aqua-100)" fillOpacity={0.6} />
            <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: 'var(--muted)' }} />
            <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: 'var(--muted)' }} width={48} />
            <Tooltip
              formatter={(value) => [`${value} Rx`, 'Prescriptions']}
              contentStyle={{ borderRadius: 0, border: '1px solid var(--ink)', fontSize: 13 }}
            />
            <Area
              type="monotone"
              dataKey="rx"
              stroke="var(--cobalt-700)"
              strokeWidth={2.5}
              fill="url(#rxFill)"
              dot={{ r: 3, fill: 'var(--cobalt-700)' }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
