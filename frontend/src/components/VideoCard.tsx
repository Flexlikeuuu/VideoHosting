import React from 'react';
import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';
import { Video } from '../types';
import { formatDate, formatDuration, formatViews } from '../utils';

interface VideoCardProps {
  video: Video;
}

export const VideoCard: React.FC<VideoCardProps> = ({ video }) => {
  return (
    <div className="flex flex-col group cursor-pointer">
      {/* Thumbnail 16:9 */}
      <Link to={`/watch/${video.id}`} className="relative aspect-video rounded-xl overflow-hidden bg-gray-200 dark:bg-[#202020]">
        <img
          src={`/api/v1/videos/${video.id}/thumbnail`}
          alt={video.title}
          className="w-full h-full object-cover group-hover:scale-105 transition duration-200"
          onError={(e) => {
            // fallback placeholder
            (e.target as HTMLImageElement).src =
              'data:image/svg+xml;charset=UTF-8,%3Csvg%20width%3D%22640%22%20height%3D%22360%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Crect%20width%3D%22100%25%22%20height%3D%22100%25%22%20fill%3D%22%23272727%22%2F%3E%3Ctext%20x%3D%2250%25%22%20y%3D%2250%25%22%20fill%3D%22%23717171%22%20font-size%3D%2220%22%20text-anchor%3D%22middle%22%20dy%3D%22.3em%22%3EYoutube%3C%2Ftext%3E%3C%2Fsvg%3E';
          }}
        />

        {/* Duration badge */}
        {video.duration_seconds !== null && video.duration_seconds !== undefined && (
          <div className="absolute bottom-2 right-2 bg-black/80 text-white text-[11px] font-medium px-1.5 py-0.5 rounded">
            {formatDuration(video.duration_seconds)}
          </div>
        )}

        {/* Private indicator badge */}
        {video.visibility === 'private' && (
          <div className="absolute top-2 left-2 bg-black/80 text-amber-400 text-xs px-2 py-0.5 rounded flex items-center gap-1 font-medium">
            <Lock className="w-3 h-3" />
            <span>Приватное</span>
          </div>
        )}
      </Link>

      {/* Info: Avatar + Title + Channel */}
      <div className="flex gap-3 mt-3">
        <Link to={`/channel/${video.owner.username}`} className="shrink-0">
          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-purple-600 to-blue-600 text-white font-semibold flex items-center justify-center text-sm">
            {video.owner.username.slice(0, 1).toUpperCase()}
          </div>
        </Link>

        <div className="flex flex-col flex-1 overflow-hidden">
          <Link
            to={`/watch/${video.id}`}
            className="font-medium text-sm leading-snug line-clamp-2 hover:text-blue-600 dark:hover:text-blue-400"
            title={video.title}
          >
            {video.title}
          </Link>

          <Link
            to={`/channel/${video.owner.username}`}
            className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 mt-1 truncate"
          >
            {video.owner.channel_name}
          </Link>

          <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-0.5">
            <span>{formatViews(video.views_count)}</span>
            <span>•</span>
            <span>{formatDate(video.created_at)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
