import React, { useEffect, useState } from 'react';
import { apiRequest } from '../api';
import { Video } from '../types';
import { VideoCard } from '../components/VideoCard';
import { Sparkles, TrendingUp } from 'lucide-react';

export const HomePage: React.FC = () => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [sort, setSort] = useState<'new' | 'popular'>('new');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFeed = async () => {
      setLoading(true);
      try {
        const data = await apiRequest<Video[]>(`/videos?sort=${sort}`);
        setVideos(data);
      } catch (err) {
        console.error('Failed to load feed:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchFeed();
  }, [sort]);

  return (
    <div className="space-y-4">
      {/* Category Pills / Sorting */}
      <div className="flex gap-2 pb-2">
        <button
          onClick={() => setSort('new')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition ${
            sort === 'new'
              ? 'bg-black text-white dark:bg-white dark:text-black'
              : 'bg-gray-100 dark:bg-[#272727] text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-[#3f3f3f]'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          <span>Новые</span>
        </button>

        <button
          onClick={() => setSort('popular')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition ${
            sort === 'popular'
              ? 'bg-black text-white dark:bg-white dark:text-black'
              : 'bg-gray-100 dark:bg-[#272727] text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-[#3f3f3f]'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>Популярные</span>
        </button>
      </div>

      {/* Grid of Video Cards */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-8">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="animate-pulse flex flex-col gap-3">
              <div className="aspect-video bg-gray-200 dark:bg-[#272727] rounded-xl"></div>
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-[#272727] shrink-0"></div>
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 dark:bg-[#272727] rounded w-5/6"></div>
                  <div className="h-3 bg-gray-200 dark:bg-[#272727] rounded w-1/2"></div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : videos.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <p className="text-lg">Видео пока нет</p>
          <p className="text-sm mt-1">Загрузите первое видео через кнопку «Создать»!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-8">
          {videos.map((video) => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      )}
    </div>
  );
};
