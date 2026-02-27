"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { ArrowLeft, Calendar, FileText, BookOpen, CheckCircle, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts";

interface HistoryItem {
  id: number;
  date: string;
  overall_score: number;
  radar_data: Record<string, number>;
  job_title: string;
  completed_courses: CompletedCourse[];
}

interface CompletedCourse {
  skill: string;
  course_title: string;
  completed_at: string;
  source: string;
}

interface RadarDataPoint {
  subject: string;
  A: number;
  B: number;
  fullMark: number;
}

export default function HistoryPage() {
  const router = useRouter();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      const token = localStorage.getItem("token");
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const res = await axios.get("http://127.0.0.1:8000/history", {
          headers: { Authorization: `Bearer ${token}` }
        });
        setHistory(res.data);
      } catch (err) {
        console.error("Failed to fetch history", err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [router]);

  const transformRadarData = (radarData: Record<string, any>): RadarDataPoint[] => {
    return Object.entries(radarData).map(([key, value]) => {
      if (typeof value === 'number') {
        return {
          subject: key,
          A: value,
          B: 100, // Default legacy JD
          fullMark: 100
        };
      } else {
        const typedValue = value as { user: number, jd: number };
        return {
          subject: key,
          A: typedValue.user,
          B: typedValue.jd,
          fullMark: 100
        };
      }
    });
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 p-8">
      <div className="container mx-auto max-w-4xl">
        <div className="flex items-center gap-4 mb-8">
          <Link href="/" className="p-2 hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded-full transition-colors">
            <ArrowLeft className="h-6 w-6" />
          </Link>
          <h1 className="text-3xl font-bold">分析历史记录</h1>
        </div>

        {loading ? (
          <div className="text-center py-12 text-zinc-500">加载中...</div>
        ) : history.length === 0 ? (
          <div className="text-center py-12 text-zinc-500">暂无历史记录，快去首页进行第一次分析吧！</div>
        ) : (
          <div className="space-y-4">
            {history.map((item) => (
              <Card key={item.id} className="overflow-hidden hover:shadow-md transition-shadow">
                <CardHeader className="bg-zinc-50/50 dark:bg-zinc-900/50 pb-4">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-4">
                      <div className={`flex items-center justify-center w-12 h-12 rounded-full text-lg font-bold ${
                        item.overall_score >= 80 ? "bg-green-100 text-green-700" :
                        item.overall_score >= 60 ? "bg-yellow-100 text-yellow-700" :
                        "bg-red-100 text-red-700"
                      }`}>
                        {item.overall_score}
                      </div>
                      <div>
                        <CardTitle className="text-lg font-bold mb-1">{item.job_title}</CardTitle>
                        <div className="flex items-center gap-2 text-xs text-zinc-500">
                          <Calendar className="h-3 w-3" />
                          {new Date(item.date).toLocaleDateString()} {new Date(item.date).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                    <Badge variant={item.overall_score > 70 ? "default" : "secondary"}>
                      {item.overall_score}% 匹配
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="h-[200px] w-full mb-6">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart cx="50%" cy="50%" outerRadius="80%" data={transformRadarData(item.radar_data)}>
                        <PolarGrid stroke="#e5e7eb" />
                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#71717a', fontSize: 12 }} />
                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                        <Radar
                          name="岗位要求"
                          dataKey="B"
                          stroke="#10b981"
                          strokeWidth={2}
                          fill="#10b981"
                          fillOpacity={0.1}
                          strokeDasharray="4 4"
                        />
                        <Radar
                          name="我的技能"
                          dataKey="A"
                          stroke="#4f46e5"
                          strokeWidth={2}
                          fill="#6366f1"
                          fillOpacity={0.4}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                  
                  {/* Completed Courses Section */}
                  {item.completed_courses && item.completed_courses.length > 0 && (
                    <div className="mt-6 pt-6 border-t border-zinc-200 dark:border-zinc-800">
                      <div className="flex items-center gap-2 mb-4">
                        <BookOpen className="h-5 w-5 text-green-600" />
                        <h3 className="font-semibold text-lg">已完成的课程</h3>
                        <Badge variant="outline" className="ml-2">
                          {item.completed_courses.length} 门
                        </Badge>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {item.completed_courses.map((course, index) => (
                          <div 
                            key={index} 
                            className="bg-zinc-50 dark:bg-zinc-900/50 rounded-lg p-4 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <CheckCircle className="h-4 w-4 text-green-500" />
                                  <span className="font-medium text-sm text-zinc-900 dark:text-zinc-100">
                                    {course.course_title}
                                  </span>
                                </div>
                                
                                <div className="flex items-center gap-3 text-xs text-zinc-600 dark:text-zinc-400 mt-2">
                                  <div className="flex items-center gap-1">
                                    <span className="font-medium">技能:</span>
                                    <Badge variant="secondary" className="text-xs px-2 py-0">
                                      {course.skill}
                                    </Badge>
                                  </div>
                                  
                                  <div className="flex items-center gap-1">
                                    <span className="font-medium">来源:</span>
                                    <span>{course.source}</span>
                                  </div>
                                </div>
                                
                                <div className="text-xs text-zinc-500 dark:text-zinc-500 mt-2">
                                  完成时间: {new Date(course.completed_at).toLocaleDateString()} {new Date(course.completed_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {item.completed_courses && item.completed_courses.length === 0 && (
                    <div className="mt-6 pt-6 border-t border-zinc-200 dark:border-zinc-800 text-center text-zinc-500 dark:text-zinc-400 text-sm">
                      <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>在此次分析时，尚未完成任何课程</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
