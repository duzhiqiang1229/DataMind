/**
 * 统一时间格式化：年月日 时分秒
 * 固定采用北京时间（Asia/Shanghai, UTC+8），不随浏览器时区变化。
 * 例：2026-08-07 13:54:42
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  // 北京时间 = UTC + 8 小时
  const utc8 = new Date(d.getTime() + 8 * 3600 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${utc8.getUTCFullYear()}-${pad(utc8.getUTCMonth() + 1)}-${pad(utc8.getUTCDate())} ` +
    `${pad(utc8.getUTCHours())}:${pad(utc8.getUTCMinutes())}:${pad(utc8.getUTCSeconds())}`
  );
}

/**
 * 短格式 Run ID：触发类型 + 北京时间（YYYY-MM-DD HH:mm:ss）。
 * 例：manual__2026-08-07T08:23:57.496907+00:00 -> 手动 2026-08-07 16:23:57
 */
export function formatRunId(
  runId: string | null | undefined,
  startDate?: string | null,
): string {
  if (!runId) return "-";
  const typeMap: Record<string, string> = {
    manual: "手动",
    scheduled: "定时",
    backfill: "补数",
    dataset_triggered: "数据触发",
  };
  const m = runId.match(/^(manual|scheduled|backfill|dataset_triggered)__?(.*)$/);
  const typeLabel = typeMap[m?.[1] || ""] || "";
  const ts = startDate || m?.[2] || runId;
  const d = new Date(ts);
  if (!Number.isNaN(d.getTime())) {
    const utc8 = new Date(d.getTime() + 8 * 3600 * 1000);
    const pad = (n: number) => String(n).padStart(2, "0");
    const date = `${utc8.getUTCFullYear()}-${pad(utc8.getUTCMonth() + 1)}-${pad(utc8.getUTCDate())}`;
    const time = `${pad(utc8.getUTCHours())}:${pad(utc8.getUTCMinutes())}:${pad(utc8.getUTCSeconds())}`;
    return typeLabel ? `${typeLabel} ${date} ${time}` : `${date} ${time}`;
  }
  return runId.length > 30 ? `${runId.slice(0, 30)}…` : runId;
}
