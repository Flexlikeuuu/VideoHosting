import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { apiRequest } from '../api';
import { Video } from '../types';
import { formatDate, formatDuration, formatViews } from '../utils';
import { Lock, Search as SearchIcon } from 'lucide-react';

export const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || '';
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!query.trim()) {
      setVideos([]);
      return;
    }

    const fetchSearch = async () => {
      setLoading(true);
      try {
        const data = await apiRequest<Video[]>(`/videos/search?q=${encodeURIComponent(query)}`);
        setVideos(data);
      } catch (err) {
        console.error('Search failed:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchSearch();
  }, [query]);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="border-b border-gray-200 dark:border-[#272727] pb-3">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <SearchIcon className="w-5 h-5 text-gray-500" />
          <span>Результаты поиска по запросу «{query}»</span>
        </h1>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="animate-pulse flex flex-col sm:flex-row gap-4">
              <div className="w-full sm:w-80 aspect-video bg-gray-200 dark:bg-[#272727] rounded-xl shrink-0"></div>
              <div className="flex-1 space-y-3 py-1">
                <div className="h-5 bg-gray-200 dark:bg-[#272727] rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 dark:bg-[#272727] rounded w-1/4"></div>
                <div className="h-3 bg-gray-200 dark:bg-[#272727] rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      ) : videos.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <p className="text-lg">По запросу «{query}» ничего не найдено</p>
          <p className="text-sm mt-1">Попробуйте изменить формулировку запроса</p>
        </div>
      ) : (
        <div className="space-y-4">
          {videos.map((video) => (
            <div
              key={video.id}
              className="flex flex-col sm:flex-row gap-4 group cursor-pointer"
            >
              {/* Horizontal Thumbnail */}
              <Link
                to={`/watch/${video.id}`}
                className="relative w-full sm:w-80 aspect-video rounded-xl overflow-hidden bg-gray-200 dark:bg-[#202020] shrink-0"
              >
                <img
                  src={`/api/v1/videos/${video.id}/thumbnail`}
                  alt={video.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition duration-200"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src =
                      'data:image/svg+xml;charset=UTF-8,%3Csvg%20width%3D%22640%22%20height%3D%22360%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Crect%20width%3D%22100%25%22%20height%3D%22100%25%22%20fill%3D%22%23272727%22%2F%3E%3Ctext%20x%3D%2250%25%22%20y%3D%2250%25%22%20fill%3D%22%23717171%22%20font-size%3D%2220%22%20text-anchor%3D%22middle%22%20dy%3D%22.3em%22%3EYoutube%3C%2Ftext%3E%3C%2Fsvg%3E';
                  }}
                />
                {video.duration_seconds !== null && video.duration_seconds !== undefined && (
                  <div className="absolute bottom-2 right-2 bg-black/80 text-white text-[11px] font-medium px-1.5 py-0.5 rounded">
                    {formatDuration(video.duration_seconds)}
                  </div>
                )}
                {video.visibility === 'private' && (
                  <div className="absolute top-2 left-2 bg-black/80 text-amber-400 text-xs px-2 py-0.5 rounded flex items-center gap-1 font-medium">
                    <Lock className="w-3 h-3" />
                    <span>Приватное</span>
                  </div>
                )}
              </Link>

              {/* Video Info */}
              <div className="flex-1 flex flex-col py-1 overflow-hidden">
                <Link
                  to={`/watch/${video.id}`}
                  className="text-base sm:text-lg font-semibold leading-snug line-clamp-2 hover:text-blue-600 dark:hover:text-blue-400"
                >
                  {video.title}
                </Link>

                <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-1">
                  <span>{formatViews(video.views_count)}</span>
                  <span>•</span>
                  <span>{formatDate(video.created_at)}</span>
                </div>

                <Link
                  to={`/channel/${video.owner.username}`}
                  className="flex items-center gap-2 mt-3 hover:opacity-80"
                >
                  <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-purple-600 to-blue-600 text-white font-semibold flex items-center justify-center text-xs shrink-0">
                    {video.owner.username.slice(0, 1).toUpperCase()}
                  </div>
                  <span className="text-xs text-gray-600 dark:text-gray-300 font-medium">
                    {video.owner.channel_name}
                  </span>
                </Link>

                {video.description && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 line-clamp-2 leading-relaxed">
                    {video.description}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
