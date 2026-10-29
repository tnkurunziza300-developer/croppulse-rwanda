import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export function DistrictChart({ data }: { data: { district: string; farms: number }[] }) {
  return <div className="chart-wrap" role="img" aria-label="Bar chart of farm profiles by district"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 8, right: 8, bottom: 28, left: -18 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8ede9" /><XAxis dataKey="district" angle={-35} textAnchor="end" tick={{ fontSize: 11, fill: '#748078' }} interval={0} /><YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#748078' }} /><Tooltip /><Bar dataKey="farms" name="Farms" fill="#43845b" radius={[5, 5, 0, 0]} maxBarSize={38} /></BarChart></ResponsiveContainer></div>;
}

export function CropChart({ data }: { data: { crop: string; activities: number }[] }) {
  return <div className="chart-wrap" role="img" aria-label="Bar chart of farmer reported activity by crop"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 8, right: 8, bottom: 28, left: -18 }}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e8ede9" /><XAxis dataKey="crop" angle={-25} textAnchor="end" tick={{ fontSize: 11, fill: '#748078' }} interval={0} /><YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#748078' }} /><Tooltip /><Bar dataKey="activities" name="Submissions" fill="#c08b45" radius={[5, 5, 0, 0]} maxBarSize={38} /></BarChart></ResponsiveContainer></div>;
}
