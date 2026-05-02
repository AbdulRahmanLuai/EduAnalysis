import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";

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
  const fileInputRef = useRef<HTMLInputElement>(null);

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

    // Clear previous error immediately when the user picks a new file
    setError("");
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      await client.post(`/projects/${id}/populate`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      // Refresh project data
      const res = await client.get(`/projects/${id}`);
      setProject(res.data);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Upload failed";
      setError(msg);
    } finally {
      setUploading(false);
      // Reset file input so the same file can be chosen again (fixes re-upload detection)
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  if (error && !project) return <div className="p-8 text-red-500">{error}</div>;
  if (!project) return <div className="p-8">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar with back button */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center h-16">
          <button
            onClick={() => navigate("/home")}
            className="text-gray-600 hover:text-gray-800 flex items-center"
          >
            <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"/></svg>
            Back to Projects
          </button>
          <h1 className="ml-4 text-xl font-bold text-gray-800">
            {project.name}
            <span className="ml-2 text-sm font-normal text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                #{project.id}
            </span>
            </h1>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto py-8 px-4">
        {/* Project details */}
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-lg font-semibold text-gray-800">Project Details</h2>
          <p className="text-gray-600 mt-2">Academic Year: {project.academic_year_start}</p>
          {project.description && (
            <>
                <p className="text-sm text-gray-500 mt-2">Description:</p>
                <p className="text-sm text-gray-600">{project.description}</p>
            </>
            )}
          <p className="text-sm mt-2">
            Status:{" "}
            <span className={project.is_populated ? "text-green-600 font-medium" : "text-yellow-600 font-medium"}>
              {project.is_populated ? "Populated" : "Not populated"}
            </span>
          </p>
        </div>

        {/* Not populated: upload + template */}
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
                  ref={fileInputRef}
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

        {/* Populated: placeholder */}
        {project.is_populated && (
          <div className="bg-white p-6 rounded-lg shadow text-center">
            <h3 className="text-xl font-semibold text-gray-800">Data Loaded Successfully</h3>
            <p className="text-gray-600 mt-2">Analytics and visualizations coming soon.</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default ProjectDetailPage;