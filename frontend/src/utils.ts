export function formatDuration(seconds?: number | null): string {
  if (!seconds || seconds <= 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

export function formatViews(views: number): string {
  if (views >= 1000000) return `${(views / 1000000).toFixed(1)} млн`;
  if (views >= 1000) return `${(views / 1000).toFixed(1)} тыс.`;
  return `${views} просмотров`;
}

export function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSec < 60) return 'только что';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)} мин. назад`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} ч. назад`;
    if (diffSec < 2592000) return `${Math.floor(diffSec / 86400)} дн. назад`;
    return date.toLocaleDateString('ru-RU');
  } catch {
    return dateString;
  }
}
