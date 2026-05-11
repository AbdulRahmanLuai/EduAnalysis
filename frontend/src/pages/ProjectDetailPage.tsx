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

  // Shared metadata
  const [students, setStudents] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [assessmentTypes, setAssessmentTypes] = useState<any[]>([]);
  const [sections, setSections] = useState<any[]>([]);

  // Student tab state
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [selectedCourseCodes, setSelectedCourseCodes] = useState<string[]>([]);
  const [studentData, setStudentData] = useState<any[]>([]);
  const [loadingStudent, setLoadingStudent] = useState(false);
  const [showWeighted, setShowWeighted] = useState(false);

  // Section analysis state
  const [sectionGrade, setSectionGrade] = useState("");
  const [sectionName, setSectionName] = useState("");
  const [sectionData, setSectionData] = useState<any[]>([]);
  const [sectionLoading, setSectionLoading] = useState(false);
  const [sectionSelectedCourse, setSectionSelectedCourse] = useState("");
  const [sectionSelectedSemester, setSectionSelectedSemester] = useState("full");
  const [sectionSelectedAssessment, setSectionSelectedAssessment] = useState("total");
  const [sectionAvailableSemesters, setSectionAvailableSemesters] = useState<number[]>([]);
  const [sectionVisType, setSectionVisType] = useState<"histogram" | "pie" | "table">("histogram");
  const [selectedStats, setSelectedStats] = useState<string[]>(["count"]);
  const [ranges, setRanges] = useState<{ min: number; max: number }[]>([
    { min: 0, max: 49 },
    { min: 50, max: 69 },
    { min: 70, max: 84 },
    { min: 85, max: 100 },
  ]);

  // Compare tab state
  const [compareGrade, setCompareGrade] = useState("");
  const [compareSections, setCompareSections] = useState<string[]>([]);
  const [compareCourse, setCompareCourse] = useState("");
  const [compareAvailCourses, setCompareAvailCourses] = useState<string[]>([]);
  const [compareAssessment, setCompareAssessment] = useState("total");
  const [compareSemester, setCompareSemester] = useState("full");
  const [compareAvailSemesters, setCompareAvailSemesters] = useState<number[]>([]);
  const [compareData, setCompareData] = useState<Record<string, number[]>>({});
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareVisType, setCompareVisType] = useState<"box" | "bar">("box");

  // ============================================================
  // Effects
  // ============================================================

  // Fetch project detail
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

  // Fetch metadata once (students, assessment types, all courses, sections)
  useEffect(() => {
    if (!project?.is_populated) return;
    const fetchMeta = async () => {
      try {
        const [studRes, assessRes, allCoursesRes, sectionsRes] = await Promise.all([
          client.get(`/projects/${id}/students`),
          client.get(`/projects/${id}/assessment-types`),
          client.get(`/projects/${id}/courses`),
          client.get(`/projects/${id}/sections`),
        ]);
        setStudents(studRes.data);
        setAssessmentTypes(assessRes.data);
        setCourses(allCoursesRes.data);
        setSections(sectionsRes.data);
      } catch (err) {
        console.error("Failed to load metadata", err);
      }
    };
    fetchMeta();
  }, [project?.is_populated, id]);

  // Fetch student-specific courses when selected student changes
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

  // Fetch section scores when grade/section changes
  useEffect(() => {
    if (!sectionGrade || !sectionName || !project?.is_populated) return;
    const fetchSection = async () => {
      setSectionLoading(true);
      try {
        const res = await client.post(`/projects/${id}/analytics/section-scores`, {
          grade: Number(sectionGrade),
          section: sectionName,
        });
        const items = res.data.items;
        setSectionData(items);
        setSectionSelectedCourse(items.length > 0 ? items[0].course_code : "");
        const sems = new Set<number>();
        items.forEach((c: any) => {
          Object.keys(c.semesters).forEach((s) => sems.add(Number(s)));
        });
        setSectionAvailableSemesters(Array.from(sems).sort());
        setSectionSelectedSemester("full");
        setSectionSelectedAssessment("total");
      } catch (err) {
        console.error("Failed to fetch section scores", err);
        setSectionData([]);
      } finally {
        setSectionLoading(false);
      }
    };
    fetchSection();
  }, [sectionGrade, sectionName, project?.is_populated, id]);

  // When compare sections change, fetch available courses and semesters
  useEffect(() => {
    if (!project?.is_populated || compareGrade === "" || compareSections.length === 0) {
      setCompareAvailCourses([]);
      setCompareAvailSemesters([]);
      setCompareCourse("");
      setCompareData({});
      return;
    }

    const fetchMeta = async () => {
      const courseSet = new Set<string>();
      const semesterSet = new Set<number>();

      try {
        for (const section of compareSections) {
          const res = await client.post(`/projects/${id}/analytics/section-scores`, {
            grade: Number(compareGrade),
            section: section,
          });
          res.data.items.forEach((item: any) => {
            courseSet.add(item.course_code);
            Object.keys(item.semesters).forEach((sem) => semesterSet.add(Number(sem)));
          });
        }

        const courses = Array.from(courseSet).sort();
        const semesters = Array.from(semesterSet).sort((a, b) => a - b);

        setCompareAvailCourses(courses);
        setCompareAvailSemesters(semesters);

        if (courses.length > 0 && !compareCourse) {
          setCompareCourse(courses[0]);
        }
        if (semesters.length > 0 && compareSemester !== "full" && !semesters.includes(Number(compareSemester))) {
          setCompareSemester("full");
        }
      } catch (err) {
        console.error("Failed to load compare metadata", err);
        setCompareAvailCourses([]);
        setCompareAvailSemesters([]);
      }
    };

    fetchMeta();
  }, [compareSections, compareGrade, project?.is_populated, id]);

  // ============================================================
  // Handlers
  // ============================================================

  const handleDownloadTemplate = async () => {
    try {
      const response = await client.get(`/projects/${id}/template`, { responseType: "blob" });
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

  const fetchCompareData = async () => {
    setCompareLoading(true);
    const newData: Record<string, number[]> = {};
    try {
      for (const section of compareSections) {
        const res = await client.post(`/projects/${id}/analytics/section-scores`, {
          grade: Number(compareGrade),
          section: section,
        });
        const courseData = res.data.items.find(
          (c: any) => c.course_code === compareCourse
        );
        if (!courseData) continue;

        const scores = extractScores(courseData, compareSemester, compareAssessment);
        newData[section] = scores;
      }
      setCompareData(newData);
    } catch (err) {
      console.error("Failed to fetch compare data", err);
      setCompareData({});
    } finally {
      setCompareLoading(false);
    }
  };

  // ============================================================
  // Helpers
  // ============================================================

  const extractScores = (courseData: any, semester: string, assessment: string): number[] => {
    if (semester === "full") {
      const studentTotals: Record<string, { sum: number; count: number }> = {};
      Object.values(courseData.semesters).forEach((sem: any) => {
        const data = assessment === "total" ? sem.total : sem.assessments?.[assessment] || [];
        data.forEach((s: number, i: number) => {
          if (!studentTotals[i]) studentTotals[i] = { sum: 0, count: 0 };
          studentTotals[i].sum += s;
          studentTotals[i].count += 1;
        });
      });
      return Object.values(studentTotals).map((v) => v.sum / v.count);
    }
    const semNum = Number(semester);
    const semData = courseData.semesters[semNum];
    if (!semData) return [];
    return assessment === "total" ? semData.total : semData.assessments?.[assessment] || [];
  };

  const pillRadio = (label: string, checked: boolean, onChange: () => void, key?: string) => (
    <label
      key={key}
      className={`px-4 py-2 rounded-full text-sm font-medium cursor-pointer transition-colors ${
        checked ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
      }`}
    >
      <input type="radio" checked={checked} onChange={onChange} className="hidden" />
      {label}
    </label>
  );

  // ============================================================
  // Chart builders
  // ============================================================

  const buildStudentChart = () => {
    if (studentData.length === 0) return null;

    const weightMap: Record<string, number> = {};
    const studentName =
      students.find((s) => s.st_external_id === selectedStudentId)?.name || selectedStudentId;
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
                text: `Performance for ${studentName}\t(ID: ${selectedStudentId})${
                  showWeighted ? " (weighted)" : ""
                }`,
                font: { size: 16, color: "#1f2937" },
              },
              xaxis: { title: { text: "Semester / Course" }, tickfont: { size: 12 } },
              yaxis: { title: { text: showWeighted ? "Weighted Score" : "Score (out of 100)" } },
              plot_bgcolor: "rgba(0,0,0,0)",
              paper_bgcolor: "rgba(0,0,0,0)",
              margin: { t: 50, r: 30, b: 70, l: 60 },
              height: 500,
              template: "plotly_white",
            } as any}
            config={{ responsive: true }}
          />
        </div>
      </div>
    );
  };

  const buildSectionChart = () => {
    if (!sectionSelectedCourse || sectionData.length === 0) return null;

    const course = sectionData.find((c: any) => c.course_code === sectionSelectedCourse);
    if (!course) return null;

    const scores = extractScores(course, sectionSelectedSemester, sectionSelectedAssessment);
    if (scores.length === 0) return <p className="text-gray-500">No data for this selection.</p>;

    const titleText = `Section ${sectionGrade}-${sectionName} – ${course.course_code} – ${
      sectionSelectedSemester === "full" ? "Full Year" : "Semester " + sectionSelectedSemester
    } – ${
      sectionSelectedAssessment === "total" ? "Weighted Total" : sectionSelectedAssessment
    }`;

    if (sectionVisType === "histogram") {
      return (
        <div className="flex justify-center mt-4">
          <div style={{ width: "100%", maxWidth: "700px" }}>
            <Plot
              data={[{ x: scores, type: "histogram", marker: { color: "#6366f1", opacity: 0.8 }, xbins: { start: 0, end: 100, size: 2 } }]}
              layout={{
                title: { text: titleText, font: { size: 14 } },
                xaxis: { title: { text: "Score" } },
                yaxis: { title: { text: "Count" } },
                plot_bgcolor: "rgba(0,0,0,0)",
                paper_bgcolor: "rgba(0,0,0,0)",
                height: 400,
                template: "plotly_white",
              } as any}
              config={{ responsive: true }}
            />
          </div>
        </div>
      );
    }

    // Pie chart
    const gradeBins = [
      { label: "0–49", min: 0, max: 49 },
      { label: "50–69", min: 50, max: 69 },
      { label: "70–84", min: 70, max: 84 },
      { label: "85–100", min: 85, max: 100 },
    ];
    const counts = gradeBins.map((bin) => scores.filter((s) => s >= bin.min && s <= bin.max).length);

    return (
      <div className="flex justify-center mt-4">
        <div style={{ width: "100%", maxWidth: "500px" }}>
          <Plot
            data={[{
              labels: gradeBins.map((b) => b.label),
              values: counts,
              type: "pie",
              hole: 0.4,
              marker: { colors: ["#ef4444", "#f59e0b", "#10b981", "#6366f1"] },
              textinfo: "label+percent",
            }]}
            layout={{ title: { text: titleText, font: { size: 14 } }, height: 400, template: "plotly_white" } as any}
            config={{ responsive: true }}
          />
        </div>
      </div>
    );
  };

  const buildSummaryTable = () => {
    if (!sectionSelectedCourse || sectionData.length === 0) return null;

    const course = sectionData.find((c: any) => c.course_code === sectionSelectedCourse);
    if (!course) return null;

    const scores = extractScores(course, sectionSelectedSemester, sectionSelectedAssessment);
    if (scores.length === 0) return <p className="text-gray-500">No data for this selection.</p>;

    const mean = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length;
    const median = (arr: number[]) => {
      const sorted = [...arr].sort((a, b) => a - b);
      const mid = Math.floor(sorted.length / 2);
      return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    };
    const stdDev = (arr: number[]) => {
      const m = mean(arr);
      return Math.sqrt(arr.reduce((sum, v) => sum + (v - m) ** 2, 0) / arr.length);
    };

    const rangeKeys = ranges.map((r) => ({ key: `${r.min}–${r.max}`, min: r.min, max: r.max }));
    const rows: { label: string; values: Record<string, string | number> }[] = [];

    const addRow = (label: string, compute: (filtered: number[]) => string | number) => {
      const values: Record<string, string | number> = {};
      rangeKeys.forEach((r) => {
        const filtered = scores.filter((s) => s >= r.min && s <= r.max);
        values[r.key] = filtered.length ? compute(filtered) : "–";
      });
      values["Overall"] = compute(scores);
      rows.push({ label, values });
    };

    if (selectedStats.includes("count")) addRow("Count", (arr) => arr.length);
    if (selectedStats.includes("mean")) addRow("Mean", (arr) => mean(arr).toFixed(1));
    if (selectedStats.includes("median")) addRow("Median", (arr) => median(arr).toFixed(1));
    if (selectedStats.includes("min")) addRow("Min", (arr) => Math.min(...arr));
    if (selectedStats.includes("max")) addRow("Max", (arr) => Math.max(...arr));
    if (selectedStats.includes("std")) addRow("Std Dev", (arr) => stdDev(arr).toFixed(1));

    if (rows.length === 0) return <p className="text-gray-500">No statistics selected.</p>;

    const columns = ["Statistic", ...rangeKeys.map((r) => r.key), "Overall"];

    return (
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-200 rounded-lg">
          <thead>
            <tr className="bg-gray-100">
              {columns.map((col) => (
                <th key={col} className="px-4 py-2 text-left text-sm font-medium text-gray-700">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx} className="border-t border-gray-200">
                <td className="px-4 py-2 text-sm font-medium text-gray-700">{row.label}</td>
                {rangeKeys.map((r) => (
                  <td key={r.key} className="px-4 py-2 text-sm text-gray-600">{row.values[r.key]}</td>
                ))}
                <td className="px-4 py-2 text-sm font-medium text-gray-700">{row.values["Overall"]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const buildCompareChart = () => {
    const traceData: any[] = [];
    const colors = ["#6366f1", "#10b981", "#f59e0b", "#ef4444"];

    Object.entries(compareData).forEach(([section, scores], idx) => {
      if (scores.length === 0) return;
      if (compareVisType === "box") {
        traceData.push({
          y: scores,
          type: "box",
          name: `Section ${section}`,
          marker: { color: colors[idx % colors.length] },
        });
      } else {
        const meanScore = scores.reduce((a, b) => a + b, 0) / scores.length;
        traceData.push({
          x: [`Section ${section}`],
          y: [meanScore],
          type: "bar",
          name: `Section ${section}`,
          marker: { color: colors[idx % colors.length] },
        });
      }
    });

    if (traceData.length === 0) return <p className="text-gray-500">No data to display.</p>;

    const title = `Compare Sections (${compareGrade}) – ${compareCourse} – ${
      compareAssessment === "total" ? "Weighted Total" : compareAssessment
    } – ${compareSemester === "full" ? "Full Year" : "Semester " + compareSemester}`;

    return (
      <div className="flex justify-center mt-4">
        <div style={{ width: "100%", maxWidth: "700px" }}>
          <Plot
            data={traceData}
            layout={{
              title: { text: title, font: { size: 14 } },
              yaxis: { title: { text: compareAssessment === "total" ? "Weighted Score" : "Score" } },
              plot_bgcolor: "rgba(0,0,0,0)",
              paper_bgcolor: "rgba(0,0,0,0)",
              height: 400,
              template: "plotly_white",
            } as any}
            config={{ responsive: true }}
          />
        </div>
      </div>
    );
  };

  // ============================================================
  // Tabs config
  // ============================================================
  const tabs = [
    { key: "student", label: "Student" },
    { key: "section", label: "Section" },
    { key: "compare", label: "Compare Sections" },
  ];

  if (error && !project) return <div className="p-8 text-red-500">{error}</div>;
  if (!project) return <div className="p-8">Loading...</div>;

  // ============================================================
  // Main render
  // ============================================================
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
        {/* Not populated – Upload UI */}
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
              <button onClick={handleDownloadTemplate} className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700">
                Download Template
              </button>
              <label className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 cursor-pointer text-center">
                {uploading ? "Uploading..." : "Upload Excel File"}
                <input type="file" accept=".xlsx,.xls" onChange={handleFileUpload} className="hidden" disabled={uploading} />
              </label>
            </div>
            {error && <p className="text-red-500 mt-4 text-sm">{error}</p>}
          </div>
        )}

        {/* Populated – Tabs */}
        {project.is_populated && (
          <div>
            <div className="flex space-x-1 bg-white rounded-lg shadow-sm border p-1 mb-6">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex-1 flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    activeTab === tab.key ? "bg-indigo-600 text-white shadow" : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              {/* ======================== STUDENT TAB ======================== */}
              {activeTab === "student" && (
                <div>
                  <div className="flex flex-wrap gap-4 mb-4 items-end">
                    <div className="flex-1 min-w-[200px]">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Student</label>
                      <select
                        value={selectedStudentId}
                        onChange={(e) => { setSelectedStudentId(e.target.value); setSelectedCourseCodes([]); }}
                        className="w-full border border-gray-300 rounded-md p-2 text-sm"
                      >
                        <option value="">-- Select student --</option>
                        {students.map((s: any) => (
                          <option key={s.st_external_id} value={s.st_external_id}>{s.name} ({s.st_external_id})</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex-1 min-w-[300px]">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Courses</label>
                      {!selectedStudentId ? (
                        <p className="text-sm text-gray-400 mt-2">Select a student to view courses</p>
                      ) : courses.length === 0 ? (
                        <p className="text-sm text-gray-400 mt-2">No courses available</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {courses.map((c: any) => (
                            <label key={c.code} className="flex items-center gap-2 bg-gray-100 px-3 py-2 rounded-md cursor-pointer hover:bg-gray-200">
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
                      )}
                    </div>
                    <button
                      onClick={fetchStudentPerformance}
                      disabled={loadingStudent || !selectedStudentId || selectedCourseCodes.length === 0}
                      className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {loadingStudent ? "Loading..." : "Load"}
                    </button>
                  </div>
                  <div className="flex items-center gap-4 mb-4">
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 cursor-pointer">
                      <input type="checkbox" checked={showWeighted} onChange={() => setShowWeighted(!showWeighted)} className="rounded" />
                      Show weighted scores
                    </label>
                  </div>
                  {buildStudentChart()}
                </div>
              )}

              {/* ======================== SECTION TAB ======================== */}
              {activeTab === "section" && (
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-4">
                    <div className="min-w-[150px]">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Grade</label>
                      <select
                        value={sectionGrade}
                        onChange={(e) => { setSectionGrade(e.target.value); setSectionName(""); }}
                        className="w-full border border-gray-300 rounded-md p-2 text-sm"
                      >
                        <option value="">-- Grade --</option>
                        {[...new Set(sections.map((s) => s.grade))].sort().map((grade) => (
                          <option key={grade} value={grade}>{grade}</option>
                        ))}
                      </select>
                    </div>
                    <div className="min-w-[150px]">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Section</label>
                      <select
                        value={sectionName}
                        onChange={(e) => setSectionName(e.target.value)}
                        className="w-full border border-gray-300 rounded-md p-2 text-sm"
                        disabled={!sectionGrade}
                      >
                        <option value="">-- Section --</option>
                        {sections.filter((s) => s.grade === sectionGrade).map((s) => (
                          <option key={s.name} value={s.name}>{s.name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="min-w-[150px]">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Semester</label>
                      <select
                        value={sectionSelectedSemester}
                        onChange={(e) => setSectionSelectedSemester(e.target.value)}
                        className="w-full border border-gray-300 rounded-md p-2 text-sm"
                        disabled={sectionAvailableSemesters.length === 0}
                      >
                        <option value="full">Full Year (average)</option>
                        {sectionAvailableSemesters.map((sem) => (
                          <option key={sem} value={sem}>Semester {sem}</option>
                        ))}
                      </select>
                    </div>
                    <div className="min-w-[150px]">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Chart Type</label>
                      <select
                        value={sectionVisType}
                        onChange={(e) => setSectionVisType(e.target.value as any)}
                        className="w-full border border-gray-300 rounded-md p-2 text-sm"
                      >
                        <option value="histogram">Histogram</option>
                        <option value="pie">Pie Chart</option>
                        <option value="table">Summary Table</option>
                      </select>
                    </div>
                  </div>

                  {/* Assessment type radio pills */}
                  <div className="flex flex-wrap gap-2">
                    {pillRadio("Total (weighted)", sectionSelectedAssessment === "total", () => setSectionSelectedAssessment("total"), "section-assess-total")}
                    {assessmentTypes.map((at: any) =>
                      pillRadio(at.name, sectionSelectedAssessment === at.name, () => setSectionSelectedAssessment(at.name), `section-assess-${at.name}`)
                    )}
                  </div>

                  {/* Course radio pills */}
                  <div className="flex flex-wrap gap-2">
                    {sectionData.map((c: any) =>
                      pillRadio(c.course_code, sectionSelectedCourse === c.course_code, () => setSectionSelectedCourse(c.course_code), `section-course-${c.course_code}`)
                    )}
                  </div>

                  {/* Summary table options */}
                  {sectionVisType === "table" && (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Statistics</label>
                        <div className="flex flex-wrap gap-4">
                          {["count", "mean", "median", "min", "max", "std"].map((stat) => (
                            <label key={stat} className="flex items-center gap-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={selectedStats.includes(stat)}
                                onChange={() =>
                                  setSelectedStats((prev) =>
                                    prev.includes(stat) ? prev.filter((s) => s !== stat) : [...prev, stat]
                                  )
                                }
                                className="rounded"
                              />
                              <span className="text-sm capitalize">{stat}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Score Ranges</label>
                        <div className="space-y-2">
                          {ranges.map((r, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                              <input
                                type="number"
                                value={r.min}
                                onChange={(e) => {
                                  const updated = [...ranges];
                                  updated[idx].min = Number(e.target.value);
                                  setRanges(updated);
                                }}
                                className="w-20 border border-gray-300 rounded p-1 text-sm"
                                placeholder="Min"
                              />
                              <span className="text-gray-500">–</span>
                              <input
                                type="number"
                                value={r.max}
                                onChange={(e) => {
                                  const updated = [...ranges];
                                  updated[idx].max = Number(e.target.value);
                                  setRanges(updated);
                                }}
                                className="w-20 border border-gray-300 rounded p-1 text-sm"
                                placeholder="Max"
                              />
                              <button
                                onClick={() => setRanges(ranges.filter((_, i) => i !== idx))}
                                className="text-red-500 hover:text-red-700"
                                title="Remove range"
                              >
                                ×
                              </button>
                            </div>
                          ))}
                          <button
                            onClick={() => setRanges([...ranges, { min: 0, max: 100 }])}
                            className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                          >
                            + Add range
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Render chart or table */}
                  {sectionLoading ? (
                    <p className="text-gray-500">Loading...</p>
                  ) : sectionVisType === "table" ? (
                    buildSummaryTable()
                  ) : (
                    buildSectionChart()
                  )}
                </div>
              )}

              {/* ======================== COMPARE TAB ======================== */}
              {activeTab === "compare" && (
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-4">
                    <div className="min-w-[150px]">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Grade</label>
                      <select
                        value={compareGrade}
                        onChange={(e) => { setCompareGrade(e.target.value); setCompareSections([]); }}
                        className="w-full border border-gray-300 rounded-md p-2 text-sm"
                      >
                        <option value="">-- Grade --</option>
                        {[...new Set(sections.map(s => s.grade))].sort().map(grade => (
                          <option key={grade} value={grade}>{grade}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex-1 min-w-[200px]">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Sections</label>
                      <div className="flex flex-wrap gap-2">
                        {sections.filter(s => s.grade === compareGrade).map(s => (
                          <label key={s.name} className="flex items-center gap-2 bg-gray-100 px-3 py-2 rounded-md cursor-pointer hover:bg-gray-200">
                            <input
                              type="checkbox"
                              checked={compareSections.includes(s.name)}
                              onChange={() =>
                                setCompareSections(prev =>
                                  prev.includes(s.name) ? prev.filter(n => n !== s.name) : [...prev, s.name]
                                )
                              }
                              className="rounded"
                            />
                            <span className="text-sm">{s.name}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="min-w-[150px]">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Semester</label>
                    <select
                      value={compareSemester}
                      onChange={(e) => setCompareSemester(e.target.value)}
                      className="w-full border border-gray-300 rounded-md p-2 text-sm"
                      disabled={compareAvailSemesters.length === 0}
                    >
                      <option value="full">Full Year (average)</option>
                      {compareAvailSemesters.map(sem => (
                        <option key={sem} value={sem}>Semester {sem}</option>
                      ))}
                    </select>
                  </div>

                  {/* Course radio pills */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Course</label>
                    <div className="flex flex-wrap gap-2">
                      {compareAvailCourses.map(code =>
                        pillRadio(code, compareCourse === code, () => setCompareCourse(code), `compare-course-${code}`)
                      )}
                    </div>
                  </div>

                  {/* Assessment type radio pills */}
                  <div className="flex flex-wrap gap-2">
                    {pillRadio("Total (weighted)", compareAssessment === "total", () => setCompareAssessment("total"), "compare-assess-total")}
                    {assessmentTypes.map((at: any) =>
                      pillRadio(at.name, compareAssessment === at.name, () => setCompareAssessment(at.name), `compare-assess-${at.name}`)
                    )}
                  </div>

                  {/* Chart type toggle */}
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" name="compareVis" value="box" checked={compareVisType === "box"} onChange={() => setCompareVisType("box")} className="text-indigo-600" />
                      <span className="text-sm">Box Plot</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" name="compareVis" value="bar" checked={compareVisType === "bar"} onChange={() => setCompareVisType("bar")} className="text-indigo-600" />
                      <span className="text-sm">Grouped Bar</span>
                    </label>
                  </div>

                  <button
                    onClick={fetchCompareData}
                    disabled={compareSections.length === 0 || !compareCourse || compareLoading}
                    className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {compareLoading ? "Loading..." : "Load"}
                  </button>

                  {compareLoading && <p className="text-gray-500">Loading...</p>}
                  {!compareLoading && Object.keys(compareData).length > 0 && buildCompareChart()}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default ProjectDetailPage;