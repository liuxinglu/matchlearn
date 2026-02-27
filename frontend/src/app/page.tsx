"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, BarChart2, CheckCircle, AlertCircle, ArrowRight, Loader2, Sparkles, BookOpen, CheckSquare, LogOut, History, RefreshCw } from "lucide-react";
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer } from "recharts";
import axios from "axios";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";

// --- Types ---
interface RadarData {
  subject: string;
  A: number; // User
  B: number; // JD
  fullMark: number;
}

interface GapDetail {
  missing_skill: string;
  importance: "High" | "Medium" | "Low";
  recommendation: string;
  recommendation_type?: string; // "course" or "project"
}

interface AnalysisResult {
  overall_score: number;
  radar_data: Record<string, number>;
  gap_details: GapDetail[];
  summary: string;
  resume_id?: number;
  jd_id?: number;
}

interface Task {
  id: number;
  skill: string;
  status: string;
  created_at: string;
}

export default function Dashboard() {
  const router = useRouter();
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jdText, setJdText] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [activeTab, setActiveTab] = useState("input");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [resumeData, setResumeData] = useState<any>(null);
  const [user, setUser] = useState<{ id: string; username?: string } | null>(null);
  const [currentJdId, setCurrentJdId] = useState<number | null>(null);
  const [resumeList, setResumeList] = useState<any[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [completingTaskId, setCompletingTaskId] = useState<number | null>(null);
  const [addingSkills, setAddingSkills] = useState<Set<string>>(new Set());

  // Mock initial data for the radar chart visualization before analysis
  const [chartData, setChartData] = useState<RadarData[]>([
    { subject: '技能', A: 0, B: 0, fullMark: 100 },
    { subject: '经验', A: 0, B: 0, fullMark: 100 },
    { subject: '教育', A: 0, B: 0, fullMark: 100 },
    { subject: '软技能', A: 0, B: 0, fullMark: 100 },
    { subject: '工具', A: 0, B: 0, fullMark: 100 },
  ]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem("token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const fetchTasks = async () => {
    const userId = localStorage.getItem("user_id");
    if (!userId) return;
    
    try {
      const res = await axios.get(`http://127.0.0.1:8000/tasks/${userId}`, {
        headers: getAuthHeaders()
      });
      setTasks(res.data);
    } catch (e) {
      console.error("Failed to fetch tasks", e);
    }
  };

  const fetchResume = async () => {
    const userId = localStorage.getItem("user_id");
    if (!userId) return;

    try {
      const res = await axios.get(`http://127.0.0.1:8000/resumes/${userId}`, {
        headers: getAuthHeaders()
      });
      setResumeData(res.data);
      if (res.data.id) {
        setCurrentResumeId(res.data.id);
      }
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 404) {
        // Resume not found is expected for new users
        setResumeData(null);
      } else {
        console.error("Failed to fetch resume", e);
      }
    }
  };

  const fetchCurrentUser = async () => {
    try {
      const res = await axios.get("http://127.0.0.1:8000/users/me", {
        headers: getAuthHeaders()
      });
      const { id, username } = res.data;
      setUser({ id: id.toString(), username });
      // Update localStorage just in case
      localStorage.setItem("user_id", id.toString());
      localStorage.setItem("username", username);
    } catch (e) {
      console.error("Failed to fetch current user", e);
      // If token is invalid, maybe logout?
      // handleLogout();
    }
  };

  const fetchResumeList = async () => {
    try {
      const res = await axios.get("http://127.0.0.1:8000/resumes/list", {
        headers: getAuthHeaders()
      });
      setResumeList(res.data);
    } catch (e) {
      console.error("Failed to fetch resume list", e);
    }
  };

  const fetchLatestAnalysis = async () => {
    try {
      const res = await axios.get("http://127.0.0.1:8000/history", {
        headers: getAuthHeaders()
      });
      if (res.data && res.data.length > 0) {
        const latest = res.data[0];
        setResult(latest);
        // Set JD ID from history so we can re-analyze
        if (latest.jd_id) setCurrentJdId(latest.jd_id);
        // Transform radar data
        const transformedRadar = Object.entries(latest.radar_data || {}).map(([key, value]) => {
          // Handle both old (number) and new ({user, jd}) formats
          if (typeof value === 'number') {
            return {
              subject: key,
              A: value,
              B: 100, // Default to 100 if no JD score available
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
        setChartData(transformedRadar);
        
        // Also fetch the JD used for this analysis if possible, or just leave JD text empty?
        // Ideally we would want to populate JD text, but history doesn't return raw JD text yet.
        // That's acceptable for now.
      }
    } catch (e) {
      console.error("Failed to fetch latest analysis", e);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("token");
    
    if (!token) {
      router.push("/login");
      return;
    }
    
    fetchCurrentUser();
    fetchTasks();
    fetchResume();
    fetchResumeList();
    fetchLatestAnalysis();
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("username");
    router.push("/login");
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setResumeFile(e.target.files[0]);
    }
  };

  const startLearning = async (skill: string, recommendation: string, recommendationType: string = 'course') => {
    if (!user) return;

    // Check for duplicate in current adding process
    if (addingSkills.has(skill)) {
      return;
    }
    
    // Check for duplicate in existing tasks
    if (tasks.some(t => t.skill === skill)) {
      toast.warning(`您已添加过 "${skill}" 的${recommendationType === 'project' ? '实践' : '学习'}任务，请继续${recommendationType === 'project' ? '实践' : '学习'}。`, {
        description: "请在右侧学习计划列表中查看。",
        action: {
          label: "知道了",
          onClick: () => {}
        }
      });
      return;
    }

    // Add to processing set
    setAddingSkills(prev => new Set(prev).add(skill));

    // 1. Open search - different search for courses vs projects
    let searchQuery = '';
    if (recommendationType === 'project') {
      // Search for project ideas and tutorials
      searchQuery = `https://www.bing.com/search?q=${skill}+project+tutorial+OR+实战项目+site:github.com+OR+site:bilibili.com+OR+site:imooc.com`;
    } else {
      // Search for learning courses
      searchQuery = `https://www.bing.com/search?q=learn+${skill}+course+教程+site:imooc.com+OR+site:bilibili.com`;
    }
    window.open(searchQuery, '_blank');
    
    // 2. Create task
    try {
      await axios.post("http://127.0.0.1:8000/tasks", {
        user_id: parseInt(user.id),
        skill_tag: skill,
        recommendation: recommendation
      }, {
        headers: getAuthHeaders()
      });
      toast.success(`已添加 "${skill}" ${recommendationType === 'project' ? '实践' : '学习'}任务到计划`);
      fetchTasks();
    } catch (e) {
      console.error("Failed to create task", e);
      toast.error("添加任务失败，请重试");
    } finally {
      // Remove from processing set after a delay
      setTimeout(() => {
        setAddingSkills(prev => {
          const newSet = new Set(prev);
          newSet.delete(skill);
          return newSet;
        });
      }, 1000);
    }
  };

  const completeTask = async (taskId: number) => {
    if (!user) return;
    
    // Prevent duplicate clicks
    if (completingTaskId === taskId) {
      return;
    }
    
    setCompletingTaskId(taskId);

    try {
      const res = await axios.post("http://127.0.0.1:8000/tasks/complete", {
        task_id: taskId,
        status: "completed"
      }, {
        headers: getAuthHeaders()
      });
      
      const suggestion = res.data.resume_suggestion;
      
      toast("恭喜！已完成任务。", {
        description: `简历更新建议：${suggestion}`,
        action: {
          label: "立即更新简历",
          onClick: () => {
            if (currentResumeId) {
              updateResume(taskId, currentResumeId);
            } else {
              toast.error("无法更新简历：未找到关联的简历记录。");
            }
          }
        },
        cancel: {
          label: "稍后",
          onClick: () => fetchTasks()
        },
        duration: 8000,
      });
      
      // Also refresh tasks immediately
      fetchTasks();

    } catch (e) {
      console.error("Failed to complete task", e);
      toast.error("操作失败，请重试");
    } finally {
      // Reset completing state after a short delay to prevent immediate re-click
      setTimeout(() => {
        setCompletingTaskId(null);
      }, 1000);
    }
  };

  const updateResume = async (taskId: number, resumeId: number) => {
    // Prevent duplicate clicks
    if (completingTaskId === taskId) {
      return;
    }
    
    setCompletingTaskId(taskId);
    
    try {
      // Note: We need the actual resume database ID here, not user_id.
      // For MVP simplifiction, let's assume we can find the resume by user_id in the backend or 
      // we fetched the resume ID in fetchResume. 
      // But wait, the previous `fetchResume` only returns JSON.
      // Let's modify the upload response to store resume ID or just assume we have it.
      // Ideally, `fetchResume` should return ID + JSON. 
      // For now, let's try to rely on the backend finding the latest resume for the user 
      // or we need to store the current resume ID in state.
      
      // Since we don't have the resume ID easily accessible in this component state from the `fetchResume` (which returns only structured_json),
      // we might need to adjust `fetchResume` or `handleAnalyze` to save the ID.
      // However, `handleAnalyze` does save `resumeId`.
      // If we are just loading the page, we don't have the resume ID unless we change the API.
      // Let's assume for this step that the user has just analyzed or we can use a workaround.
      
      // WORKAROUND: Pass user_id as resume_id if backend supports it? No.
      // BETTER FIX: Let's assume the user has to re-analyze to get the resume ID for now, 
      // OR we update `get_latest_resume` to return the ID too.
      // Given the constraints, let's use the ID from `handleAnalyze` if available, or fail gracefully.

      // Actually, looking at `handleAnalyze`, we get `resumeRes.data.id`.
      // If we are reloading the page, we can't update resume easily without fetching the ID.
      // Let's rely on the analysis flow for updates for now.
      
      // Wait, `update_resume_from_task` requires `resume_id`.
      // Let's check `handleAnalyze` scope.
      
      // Let's use a temporary state for currentResumeId
      
      await axios.post("http://127.0.0.1:8000/resumes/update-from-task", {
        task_id: taskId,
        resume_id: resumeId
      }, {
        headers: getAuthHeaders()
      });
      toast.success("简历已更新！正在重新分析匹配度...");
      await fetchResume(); // Refresh resume preview
      await fetchTasks(); // Refresh task list status
      
      // Auto re-analyze to show score improvement
      if (currentResumeId && currentJdId) {
        // Wait a moment for resume update to propagate
        setTimeout(() => {
          reAnalyze();
        }, 500);
      }
    } catch (e) {
      console.error("Failed to update resume", e);
      toast.error("更新简历失败，请重试。");
    } finally {
      // Reset completing state after a short delay to prevent immediate re-click
      setTimeout(() => {
        setCompletingTaskId(null);
      }, 1000);
    }
  };
  
  // We need to store the resume ID from analysis to allow updates
  const [currentResumeId, setCurrentResumeId] = useState<number | null>(null);

  const reAnalyze = async () => {
    if (!currentResumeId || !currentJdId || !user) return;

    setIsAnalyzing(true);
    setActiveTab("results");

    try {
      // Perform Gap Analysis using existing IDs, forcing analysis
      const analysisRes = await axios.post("http://127.0.0.1:8000/gap-analysis", {
        resume_id: currentResumeId,
        jd_id: currentJdId,
        force_analyze: true
      }, {
        headers: getAuthHeaders()
      });

      const data = analysisRes.data;
      setResult(data);

      const transformedRadar = Object.entries(data.radar_data || {}).map(([key, value]) => {
        // Handle both old (number) and new ({user, jd}) formats
        if (typeof value === 'number') {
          return {
            subject: key,
            A: value,
            B: 100, // Default to 100 if no JD score available
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
      setChartData(transformedRadar);

    } catch (error) {
      console.error("Re-analysis failed:", error);
      toast.error("重新分析失败，请稍后重试。");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAnalyze = async () => {
    if ((!resumeFile && !selectedResumeId) || !jdText || !user) return;

    setIsAnalyzing(true);
    setActiveTab("results");

    try {
      let resumeId = selectedResumeId;

      // 1. Upload Resume (if new file selected)
      if (resumeFile) {
        const formData = new FormData();
        formData.append("user_id", user.id);
        formData.append("file", resumeFile);
        
        const resumeRes = await axios.post("http://127.0.0.1:8000/resumes/upload", formData, {
          headers: { 
            "Content-Type": "multipart/form-data",
            ...getAuthHeaders() 
          },
        });
        resumeId = resumeRes.data.id;
        fetchResumeList(); // Refresh list after upload
      }

      if (!resumeId) throw new Error("No resume ID");
      setCurrentResumeId(resumeId);

      // 2. Submit JD (title will be extracted from JD text by backend LLM)
      const jdRes = await axios.post("http://127.0.0.1:8000/jds", {
        title: "Target Role", // Placeholder, will be replaced by extracted title from JD text
        description: jdText,
      }, {
        headers: getAuthHeaders()
      });
      const jdId = jdRes.data.id;
      setCurrentJdId(jdId);

      // 3. Perform Gap Analysis (Cached by default)
      const analysisRes = await axios.post("http://127.0.0.1:8000/gap-analysis", {
        resume_id: resumeId,
        jd_id: jdId,
        force_analyze: false 
      }, {
        headers: getAuthHeaders()
      });

      const data = analysisRes.data;
      setResult(data);

      // Transform radar data for Recharts
      const transformedRadar = Object.entries(data.radar_data || {}).map(([key, value]) => {
        // Handle both old (number) and new ({user, jd}) formats
        if (typeof value === 'number') {
          return {
            subject: key,
            A: value,
            B: 100, // Default to 100 if no JD score available
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
      setChartData(transformedRadar);

    } catch (error) {
      console.error("Analysis failed:", error);
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        router.push("/login");
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/30">
              M
            </div>
            <span className="font-bold text-xl tracking-tight">MatchLearn 职场匹配</span>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-zinc-600 dark:text-zinc-400">
            <a href="#" className="text-indigo-600 dark:text-indigo-400 font-semibold">仪表盘</a>
            <a href="/history" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors flex items-center gap-1">
              <History className="h-4 w-4" /> 历史记录
            </a>
            <button onClick={handleLogout} className="hover:text-red-600 dark:hover:text-red-400 transition-colors flex items-center gap-1">
              <LogOut className="h-4 w-4" /> 退出
            </button>
          </nav>
          <div className="h-8 w-8 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-indigo-700 dark:text-indigo-300 font-bold text-xs" title={user?.username}>
            {user?.username ? user.username.charAt(0).toUpperCase() : "?"}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Inputs */}
        <div className="lg:col-span-5 space-y-6">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
              人岗匹配分析
            </h1>
            <p className="text-zinc-500 dark:text-zinc-400">
              上传简历并输入目标职位描述，发现您的专属学习路径。
            </p>
          </div>

          <Card className="border-zinc-200 dark:border-zinc-800 shadow-sm overflow-hidden">
            <CardHeader className="bg-zinc-50/50 dark:bg-zinc-900/50 pb-4">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <FileText className="h-4 w-4 text-indigo-500" />
                简历与职位描述
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
              {/* Resume Upload */}
              <div className="space-y-4">
                <Label htmlFor="resume" className="text-base font-semibold flex items-center gap-2">
                  <Upload className="h-4 w-4" /> 上传简历 (PDF)
                </Label>
                
                {/* Resume List Selection */}
                {resumeList.length > 0 && (
                  <div className="mb-4">
                    <Label className="text-sm text-zinc-500 mb-2 block">或选择已上传的简历：</Label>
                    <div className="grid grid-cols-1 gap-2 max-h-40 overflow-y-auto border rounded p-2">
                      {resumeList.map((r) => (
                        <div 
                            key={r.id} 
                            onClick={() => {
                              setSelectedResumeId(r.id);
                              setResumeFile(null); 
                              console.log("Selected resume:", r.id);
                            }}
                            className={`p-2 rounded cursor-pointer text-sm flex justify-between items-center transition-all duration-200 border ${
                              selectedResumeId === r.id 
                                ? "bg-indigo-100 dark:bg-indigo-900 border-indigo-500 shadow-sm" 
                                : "border-transparent hover:bg-zinc-100 dark:hover:bg-zinc-800"
                            }`}
                          >
                          <span className="font-medium truncate">{r.name}</span>
                          <span className="text-xs text-zinc-500">{new Date(r.created_at).toLocaleDateString()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  resumeFile ? "border-indigo-500 bg-indigo-50/50 dark:bg-indigo-900/20" : "border-zinc-300 dark:border-zinc-700 hover:border-indigo-400"
                }`}>
                  <Input 
                    id="resume" 
                    type="file" 
                    accept=".pdf" 
                    onChange={(e) => {
                      handleFileUpload(e);
                      setSelectedResumeId(null); // Clear selection if uploading new
                    }}
                    className="hidden" 
                  />
                  <Label htmlFor="resume" className="cursor-pointer block">
                    {resumeFile ? (
                      <div className="flex flex-col items-center gap-2 text-indigo-600 dark:text-indigo-400">
                        <CheckCircle className="h-8 w-8" />
                        <span className="font-medium">{resumeFile.name}</span>
                        <span className="text-xs text-zinc-500">点击更换文件</span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-2 text-zinc-500">
                        <Upload className="h-8 w-8 mb-2" />
                        <span className="font-medium">点击上传或拖拽文件至此</span>
                        <span className="text-xs">支持 PDF 格式 (最大 10MB)</span>
                      </div>
                    )}
                  </Label>
                </div>
              </div>

              <Separator />

              {/* JD Input */}
              <div className="space-y-2">
                <Label htmlFor="jd" className="text-sm font-medium">职位描述 (JD)</Label>
                <Textarea
                  id="jd"
                  placeholder="在此粘贴职位描述..."
                  className="min-h-[200px] resize-none focus-visible:ring-indigo-500"
                  value={jdText}
                  onChange={(e) => setJdText(e.target.value)}
                />
              </div>
            </CardContent>
            <CardFooter className="bg-zinc-50/50 dark:bg-zinc-900/50 pt-6">
              <Button 
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-500/20 transition-all"
                size="lg"
                onClick={handleAnalyze}
                disabled={isAnalyzing || (!resumeFile && !selectedResumeId) || !jdText}
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    正在分析...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    开始匹配分析
                  </>
                )}
              </Button>
            </CardFooter>
          </Card>

          {/* Resume Preview - Moved to Left Column */}
          {resumeData && (
            <Card className="border-zinc-200 dark:border-zinc-800 shadow-sm overflow-hidden">
              <CardHeader className="bg-zinc-50/50 dark:bg-zinc-900/50 pb-4">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <FileText className="h-4 w-4 text-indigo-500" />
                  我的简历预览 (实时更新)
                </CardTitle>
                <CardDescription>
                  您的学习成果将实时同步到此处。
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="bg-white dark:bg-zinc-900 shadow-sm p-6 rounded-lg border border-zinc-200 dark:border-zinc-800 text-sm max-h-[500px] overflow-y-auto">
                  {/* Header */}
                  <div className="border-b border-zinc-200 dark:border-zinc-800 pb-4 mb-4">
                    <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">{resumeData.name || "姓名"}</h2>
                    <div className="text-zinc-500 dark:text-zinc-400 mt-1 flex gap-4 text-xs">
                      <span>{resumeData.email || "邮箱"}</span>
                    </div>
                  </div>

                  {/* Skills */}
                  <div className="mb-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2 border-b border-zinc-100 dark:border-zinc-800 pb-1">技能 (Skills)</h4>
                    <div className="flex flex-wrap gap-1">
                      {resumeData.skills?.map((skill: string, i: number) => (
                        <span key={i} className="px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded text-[10px]">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Experience */}
                  <div className="mb-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2 border-b border-zinc-100 dark:border-zinc-800 pb-1">工作经历 (Experience)</h4>
                    {resumeData.experience?.map((exp: any, i: number) => (
                      <div key={i} className="mb-3 last:mb-0">
                        <div className="flex justify-between items-baseline">
                          <h5 className="font-bold text-zinc-900 dark:text-zinc-100">{exp.title}</h5>
                          <span className="text-zinc-500 text-[10px]">{exp.duration}</span>
                        </div>
                        <div className="text-indigo-600 dark:text-indigo-400 font-medium text-[10px] mb-0.5">{exp.company}</div>
                        <p className="text-zinc-600 dark:text-zinc-400 leading-snug text-xs">{exp.description}</p>
                      </div>
                    ))}
                  </div>

                  {/* Projects */}
                  <div className="mb-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2 border-b border-zinc-100 dark:border-zinc-800 pb-1">项目经历 (Projects)</h4>
                    {resumeData.projects?.map((proj: any, i: number) => (
                      <div key={i} className="mb-3 last:mb-0 p-3 bg-zinc-50 dark:bg-zinc-800/30 rounded border border-zinc-100 dark:border-zinc-800/50">
                        <div className="font-bold text-zinc-900 dark:text-zinc-100">{proj.name}</div>
                        <p className="text-zinc-600 dark:text-zinc-400 mt-1 leading-snug text-xs">{proj.description}</p>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {proj.technologies?.map((tech: string, j: number) => (
                            <Badge key={j} variant="outline" className="text-[10px] h-4 font-normal px-1">
                              {tech}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Education */}
                  <div className="mb-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2 border-b border-zinc-100 dark:border-zinc-800 pb-1">教育经历 (Education)</h4>
                    {resumeData.education?.map((edu: any, i: number) => (
                      <div key={i} className="mb-2">
                        <div className="flex justify-between">
                          <h5 className="font-bold text-zinc-900 dark:text-zinc-100">{edu.school}</h5>
                          <span className="text-zinc-500 text-[10px]">{edu.year}</span>
                        </div>
                        <div className="text-zinc-600 dark:text-zinc-400 text-xs">{edu.degree}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column: Results */}
        <div className="lg:col-span-7 space-y-6">
          <AnimatePresence mode="wait">
            {!result && !isAnalyzing ? (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="h-full min-h-[500px] flex flex-col items-center justify-center text-center p-8 border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl bg-zinc-50/50 dark:bg-zinc-900/50"
              >
                <div className="h-16 w-16 bg-zinc-100 dark:bg-zinc-800 rounded-full flex items-center justify-center mb-4">
                  <BarChart2 className="h-8 w-8 text-zinc-400" />
                </div>
                <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-100">准备就绪</h3>
                <p className="text-sm text-zinc-500 max-w-xs mt-2">
                  提交您的简历和目标职位描述，查看技能匹配雷达图和个性化学习路径。
                </p>
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-6"
              >
                {/* Score & Radar Section */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Overall Score Card */}
                  <Card className="border-indigo-100 dark:border-indigo-900/50 bg-gradient-to-br from-white to-indigo-50/50 dark:from-zinc-900 dark:to-indigo-950/20">
                    <CardHeader>
                      <CardTitle className="text-sm font-medium text-zinc-500 uppercase tracking-wider">整体匹配度</CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col items-center justify-center py-6">
                      <div className="relative flex items-center justify-center">
                        <svg className="h-32 w-32 -rotate-90 transform">
                          <circle cx="64" cy="64" r="60" fill="none" stroke="currentColor" strokeWidth="8" className="text-zinc-200 dark:text-zinc-800" />
                          <circle 
                            cx="64" cy="64" r="60" fill="none" stroke="currentColor" strokeWidth="8" 
                            className="text-indigo-600 transition-all duration-1000 ease-out"
                            strokeDasharray={2 * Math.PI * 60}
                            strokeDashoffset={2 * Math.PI * 60 * (1 - (result?.overall_score || 0) / 100)}
                          />
                        </svg>
                        <span className="absolute text-4xl font-bold text-zinc-900 dark:text-white">
                          {result?.overall_score || 0}<span className="text-lg text-zinc-400">%</span>
                        </span>
                      </div>
                      <p className="mt-4 text-sm font-medium text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 px-3 py-1 rounded-full">
                        {result?.overall_score && result.overall_score > 70 ? "匹配度很高！" : "仍需努力"}
                      </p>
                    </CardContent>
                  </Card>

                  {/* Radar Chart Card */}
                  <Card className="overflow-hidden">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-zinc-500 uppercase tracking-wider">技能雷达</CardTitle>
                    </CardHeader>
                    <CardContent className="h-[250px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={chartData}>
                          <PolarGrid stroke="#e5e7eb" />
                          <PolarAngleAxis dataKey="subject" tick={{ fill: '#71717a', fontSize: 12 }} />
                          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                          {/* JD Requirements Radar */}
                          <Radar
                            name="岗位要求"
                            dataKey="B"
                            stroke="#10b981"
                            strokeWidth={2}
                            fill="#10b981"
                            fillOpacity={0.1}
                            strokeDasharray="4 4"
                          />
                          {/* User Skills Radar */}
                          <Radar
                            name="我的技能"
                            dataKey="A"
                            stroke="#4f46e5"
                            strokeWidth={3}
                            fill="#6366f1"
                            fillOpacity={0.4}
                          />
                          {/* Legend could be added here if Recharts supports it easily, or just labels above */}
                        </RadarChart>
                        <div className="absolute top-2 right-2 flex flex-col gap-1 text-xs">
                          <div className="flex items-center gap-1">
                            <div className="w-3 h-3 bg-indigo-500/40 border border-indigo-600 rounded-sm"></div>
                            <span className="text-zinc-600 dark:text-zinc-400">我的技能</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <div className="w-3 h-3 bg-emerald-500/10 border border-emerald-500 border-dashed rounded-sm"></div>
                            <span className="text-zinc-600 dark:text-zinc-400">岗位要求</span>
                          </div>
                        </div>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </div>

                {/* Gap Details & Learning Path */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertCircle className="h-5 w-5 text-amber-500" />
                      差距分析与建议
                    </CardTitle>
                    <CardDescription>
                      为您规划的优先级学习路径，助您补齐技能短板。
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-0">
                    <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                      {(result?.gap_details || []).map((gap, index) => (
                        <motion.div 
                          key={index}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.1 }}
                          className="py-4 flex flex-col sm:flex-row gap-4 sm:items-start group hover:bg-zinc-50 dark:hover:bg-zinc-900/50 p-4 rounded-lg transition-colors"
                        >
                          <div className="min-w-[120px]">
                            <Badge 
                              variant={gap.importance === "High" ? "destructive" : gap.importance === "Medium" ? "default" : "secondary"}
                              className="mb-2"
                            >
                              {gap.importance === "High" ? "高" : gap.importance === "Medium" ? "中" : "低"} 优先级
                            </Badge>
                            <h4 className="font-semibold text-zinc-900 dark:text-zinc-100">{gap.missing_skill}</h4>
                          </div>
                          
                          <div className="flex-1 space-y-2">
                            <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                              {gap.recommendation}
                              {gap.recommendation_type && (
                                <span className="ml-2 text-xs text-zinc-500">
                                  (类型: {gap.recommendation_type})
                                </span>
                              )}
                            </p>
                            {/* 对于错误类型的技能推荐，不显示开始学习按钮 */}
                            {!gap.missing_skill.includes('数据不完整') && (
                              <Button 
                                variant="outline" 
                                size="sm" 
                                className={`h-8 text-xs gap-1 ${addingSkills.has(gap.missing_skill) ? 'cursor-not-allowed opacity-70' : 'group-hover:border-indigo-200 dark:group-hover:border-indigo-900 group-hover:text-indigo-600 dark:group-hover:text-indigo-400'} transition-all`}
                                onClick={() => startLearning(gap.missing_skill, gap.recommendation, gap.recommendation_type)}
                                disabled={addingSkills.has(gap.missing_skill)}
                              >
                                {addingSkills.has(gap.missing_skill) ? (
                                  <>
                                    <Loader2 className="h-3 w-3 animate-spin" /> 添加中...
                                  </>
                                ) : (
                                  <>
                                    {gap.recommendation_type === 'project' ? '开始实践' : '开始学习'} <ArrowRight className="h-3 w-3" />
                                  </>
                                )}
                              </Button>
                            )}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Learning Plan */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BookOpen className="h-5 w-5 text-indigo-500" />
                      我的学习计划
                    </CardTitle>
                    <CardDescription>
                      已添加的学习任务列表。
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {tasks.length === 0 ? (
                      <div className="text-center py-8 text-zinc-500 text-sm">
                        暂无学习任务，请从上方差距分析中添加。
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {tasks.map((task) => (
                          <div key={task.id} className="flex items-center justify-between p-3 bg-zinc-50 dark:bg-zinc-900/50 rounded-lg border border-zinc-100 dark:border-zinc-800">
                            <div className="flex items-center gap-3">
                              <div className={`h-2 w-2 rounded-full ${task.status === 'completed' || task.status === 'verified' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                              <span className="font-medium text-sm">{task.skill}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-xs">
                                {task.status === 'completed' || task.status === 'verified' ? '已完成' : '进行中'}
                              </Badge>
                              {task.status === 'completed' && (
                                <Button 
                                  variant="ghost" 
                                  size="icon" 
                                  className={`h-6 w-6 ${completingTaskId === task.id ? 'text-gray-400 cursor-not-allowed' : 'text-blue-600 hover:text-blue-700 hover:bg-blue-50'}`}
                                  onClick={() => {
                                    if (currentResumeId) {
                                      updateResume(task.id, currentResumeId);
                                    } else {
                                      toast.error("无法更新简历：请先上传或选择一份简历。");
                                    }
                                  }}
                                  disabled={completingTaskId === task.id}
                                  title={completingTaskId === task.id ? "处理中..." : "更新简历"}
                                >
                                  {completingTaskId === task.id ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                  ) : (
                                    <RefreshCw className="h-4 w-4" />
                                  )}
                                </Button>
                              )}
                              {task.status !== 'completed' && task.status !== 'verified' && (
                                <Button 
                                  variant="ghost" 
                                  size="icon" 
                                  className={`h-6 w-6 ${completingTaskId === task.id ? 'text-gray-400 cursor-not-allowed' : 'text-green-600 hover:text-green-700 hover:bg-green-50'}`}
                                  onClick={() => completeTask(task.id)}
                                  disabled={completingTaskId === task.id}
                                  title={completingTaskId === task.id ? "处理中..." : "标记为完成"}
                                >
                                  {completingTaskId === task.id ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                  ) : (
                                    <CheckSquare className="h-4 w-4" />
                                  )}
                                </Button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
