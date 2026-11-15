export interface User {
  id: string;
  email: string;
  username: string;
  role: 'user' | 'moderator' | 'admin';
  channel_name: string;
  channel_description?: string | null;
  avatar_key?: string | null;
  created_at: string;
}

export interface Video {
  id: string;
  title: string;
  description?: string | null;
  status: 'uploading' | 'processing' | 'ready' | 'failed';
  visibility: 'public' | 'private';
  is_hidden: boolean;
  hidden_reason?: string | null;
  duration_seconds?: number | null;
  views_count: number;
  likes_count: number;
  dislikes_count: number;
  thumbnail_object_key?: string | null;
  created_at: string;
  owner: User;
}

export interface Comment {
  id: string;
  video_id: string;
  author: User;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface ChannelProfile {
  id: string;
  username: string;
  channel_name: string;
  channel_description?: string | null;
  avatar_key?: string | null;
  subscribers_count: number;
  is_subscribed: boolean;
  videos_count: number;
  created_at: string;
}

export interface Playlist {
  id: string;
  title: string;
  description?: string | null;
  is_public: boolean;
  owner: User;
  items: Array<{
    id: string;
    position: number;
    video: Video;
    added_at: string;
  }>;
  created_at: string;
}

export interface Report {
  id: string;
  video_id: string;
  reporter: User;
  reason: string;
  status: 'pending' | 'resolved' | 'dismissed';
  moderator?: User | null;
  moderator_comment?: string | null;
  created_at: string;
}

export interface VideoAccessGrant {
  id: string;
  video_id: string;
  user: {
    id: string;
    username: string;
    email: string;
    channel_name: string;
  };
  created_at: string;
}
