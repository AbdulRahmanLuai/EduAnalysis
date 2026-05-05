import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import Plot from "react-plotly.js";

interface Project {
  id: number;
  name: string;
  academic_year_start: number;
  description?: string;
  is_populated: boolean;
}

const ProjectDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [activeTab, setActiveTab] = useState("student");

  // Student analytics state
  const [students, setStudents] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [assessmentTypes, setAssessmentTypes] = useState<any[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [selectedCourseCodes, setSelectedCourseCodes] = useState<string[]>([]);
  const [studentData, setStudentData] = useState<any[]>([]);
  const [loadingStudent, setLoadingStudent] = useState(false);
  const [showWeighted, setShowWeighted] = useState(false);

  // ---------- Fetch project ----------
  useEffect(() => {
    const fetchProject = async () => {
      try {
        const res = await client.get(`/projects/${id}`);
        setProject(res.data);
      } catch (err: any) {
        setError("Failed to load project.");
      }
    };
    fetchProject();
  }, [id]);

  // ---------- Fetch students & assessment types once ----------
  useEffect(() => {
    if (!project?.is_populated) return;
    const fetchMeta = async () => {
      try {
        const [studRes, assessRes] = await Promise.all([
          client.get(`/projects/${id}/students`),
          client.get(`/projects/${id}/assessment-types`),
        ]);
        setStudents(studRes.data);
        setAssessmentTypes(assessRes.data);
      } catch (err) {
        console.error("Failed to load metadata", err);
      }
    };
    fetchMeta();
  }, [project?.is_populated, id]);

  // ---------- Fetch courses when selected student changes ----------
  useEffect(() => {
    if (!selectedStudentId || !project?.is_populated) {
      setCourses([]);
      setSelectedCourseCodes([]);
      return;
    }
    const fetchCourses = async () => {
      try {
        const res = await client.get(`/projects/${id}/courses`, {
          params: { student_id: selectedStudentId },
        });
        setCourses(res.data);
        setSelectedCourseCodes((prev) =>
          prev.filter((code) => res.data.some((c: any) => c.code === code))
        );
      } catch (err) {
        console.error("Failed to load courses", err);
      }
    };
    fetchCourses();
  }, [selectedStudentId, project?.is_populated, id]);

  // ---------- Other handlers ----------
  const handleDownloadTemplate = async () => {
    try {
      const response = await client.get(`/projects/${id}/template`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `project_${id}_template.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Could not download template.");
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await client.post(`/projects/${id}/populate`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const res = await client.get(`/projects/${id}`);
      setProject(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleCourseToggle = (code: string) => {
    setSelectedCourseCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const fetchStudentPerformance = async () => {
    if (!selectedStudentId || selectedCourseCodes.length === 0) return;
    setLoadingStudent(true);
    setError("");
    try {
      const res = await client.post(`/projects/${id}/analytics/student-performance`, {
        student_external_id: selectedStudentId,
        course_codes: selectedCourseCodes,
      });
      setStudentData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load student data");
      setStudentData([]);
    } finally {
      setLoadingStudent(false);
    }
  };

  // ---------- Build modern student chart ----------
  const buildStudentChart = () => {
    if (studentData.length === 0) return null;

    const weightMap: Record<string, number> = {};
    const studentName = students.find(s => s.st_external_id === selectedStudentId)?.name || selectedStudentId;
    assessmentTypes.forEach((at: any) => {
      weightMap[at.name] = at.weight;
    });

    const colorPalette = ["#6366f1", "#10b981", "#f59e0b", "#ef4444"];
    const traces: any[] = [];
    const grouped: Record<string, { labels: [number, string][]; scores: number[] }> = {};

    studentData.forEach((d: any) => {
      const score = showWeighted ? d.score * (weightMap[d.assessment_type] / 100) : d.score;
      if (!grouped[d.assessment_type]) {
        grouped[d.assessment_type] = { labels: [], scores: [] };
      }
      grouped[d.assessment_type].labels.push([d.semester_number, d.course_code]);
      grouped[d.assessment_type].scores.push(score);
    });

    Object.entries(grouped).forEach(([asType, data], idx) => {
      traces.push({
        x: data.labels.map((l) => `S${l[0]} - ${l[1]}`),
        y: data.scores,
        type: "bar",
        name: asType,
        marker: { color: colorPalette[idx % colorPalette.length], opacity: 0.85 },
      });
    });

    return (
      <div className="flex justify-center mt-6">
        <div style={{ width: "100%", maxWidth: "800px" }}>
          <Plot
            data={traces}
            layout={{
              barmode: "group",
              title: {
                text: `Performance for ${studentName}\t(ID: ${selectedStudentId})${showWeighted ? " (weighted)" : ""}`,
                font: { size: 16, color: "#1f2937" },
              },
              xaxis: {
                title: { text: "Semester / Course" },
                tickfont: { size: 12 },
              },
              yaxis: {
                title: { text: showWeighted ? "Weighted Score" : "Score (out of 100)" },
              },
              plot_bgcolor: "rgba(0,0,0,0)",
              paper_bgcolor: "rgba(0,0,0,0)",
              margin: { t: 50, r: 30, b: 70, l: 60 },
              height: 500,
              template: "plotly_white" as const,
            } as any}
            config={{ responsive: true }}
          />
        </div>
      </div>
    );
  };

  // ---------- Constants for tabs & sample charts ----------
  const overviewChart = (
    <Plot
      data={[{ x: ["MATH101", "SCI101"], y: [78.5, 85.2], type: "bar", marker: { color: "#6366f1" } }]}
      layout={{ title: { text: "Average Weighted Score per Course" }, height: 300 }}
      useResizeHandler
    />
  );

  const sectionChart = (
    <Plot
      data={[{ x: [55, 65, 75, 85, 95], type: "histogram", name: "Scores", marker: { color: "#10b981" } }]}
      layout={{ title: { text: "Score Distribution (Section A)" }, height: 300 }}
      useResizeHandler
    />
  );

  const compareChart = (
    <Plot
      data={[
        { y: [70, 75, 80, 85, 90], type: "box", name: "Section A" },
        { y: [60, 65, 70, 75, 80], type: "box", name: "Section B" },
      ]}
      layout={{ title: { text: "Section Score Comparison" }, height: 300 }}
      useResizeHandler
    />
  );

  const tabs = [
    { key: "overview", label: "Overview", icon: "📊" },
    { key: "student", label: "Student", icon: "🧑‍🎓" },
    { key: "section", label: "Section", icon: "📐" },
    { key: "compare", label: "Compare", icon: "⚖️" },
  ];

  if (error && !project) return <div className="p-8 text-red-500">{error}</div>;
  if (!project) return <div className="p-8">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center h-16">
          <button onClick={() => navigate("/home")} className="text-gray-600 hover:text-gray-800 flex items-center">
            <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          <h1 className="ml-4 text-xl font-bold text-gray-800">
            {project.name}
            <span className="ml-2 text-sm font-normal text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
              #{project.id}
            </span>
          </h1>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-8 px-4">
        {!project.is_populated && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Upload Student Data</h3>
            <ol className="list-decimal list-inside text-gray-600 space-y-2 mb-6">
              <li>Download the Excel template.</li>
              <li>Fill it with your data (do not change column headers).</li>
              <li>Upload the completed file below.</li>
              <li>Once processed, analytics will be available.</li>
            </ol>
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={handleDownloadTemplate}
                className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
              >
                Download Template
              </button>
              <label className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 cursor-pointer text-center">
                {uploading ? "Uploading..." : "Upload Excel File"}
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileUpload}
                  className="hidden"
                  disabled={uploading}
                />
              </label>
            </div>
            {error && <p className="text-red-500 mt-4 text-sm">{error}</p>}
          </div>
        )}

        {project.is_populated && (
          <div>
            {/* Tabs */}
            <div className="flex space-x-1 bg-white rounded-lg shadow-sm border p-1 mb-6">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex-1 flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    activeTab === tab.key
                      ? "bg-indigo-600 text-white shadow"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="bg-white rounded-lg shadow p-6">
              {activeTab === "overview" && (<p>
                    some overview. 
              </p>)}
              {activeTab === "student" && (
                <div>
                  <div className="flex flex-wrap gap-4 mb-4 items-end">
                    <div className="flex-1 min-w-[200px]">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Student</label>
                      <select
                        value={selectedStudentId}
                        onChange={(e) => {
                          setSelectedStudentId(e.target.value);
                          setSelectedCourseCodes([]);
                        }}
                        className="w-full border border-gray-300 rounded-md p-2 text-sm"
                      >
                        <option value="">-- Select student --</option>
                        {students.map((s: any) => (
                          <option key={s.st_external_id} value={s.st_external_id}>
                            {s.name} ({s.st_external_id})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="flex-1 min-w-[300px]">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Courses</label>
                      <div className="flex flex-wrap gap-2">
                        {courses.map((c: any) => (
                          <label
                            key={c.code}
                            className="flex items-center gap-2 bg-gray-100 px-3 py-2 rounded-md cursor-pointer hover:bg-gray-200"
                          >
                            <input
                              type="checkbox"
                              checked={selectedCourseCodes.includes(c.code)}
                              onChange={() => handleCourseToggle(c.code)}
                              className="rounded"
                            />
                            <span className="text-sm">{c.code}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <button
                      onClick={fetchStudentPerformance}
                      disabled={loadingStudent || !selectedStudentId || selectedCourseCodes.length === 0}
                      className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {loadingStudent ? "Loading..." : "Load"}
                    </button>
                  </div>

                  {/* Weighted toggle */}
                  <div className="flex items-center gap-4 mb-4">
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={showWeighted}
                        onChange={() => setShowWeighted(!showWeighted)}
                        className="rounded"
                      />
                      Show weighted scores
                    </label>
                  </div>

                  {buildStudentChart()}
                </div>
              )}

              {activeTab === "section" && sectionChart}
              {activeTab === "compare" && compareChart}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default ProjectDetailPage;