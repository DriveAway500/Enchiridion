use plotters::prelude::*;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use serde::Deserialize;
use std::f64::consts::PI;
use std::sync::Arc;
use tokio::task;
use usvg::TreeParsing;

// ---------------------------------------------------------------------------
// Structs for deserializing NVD/CVE JSON structures
// ---------------------------------------------------------------------------

#[derive(Deserialize, Debug)]
struct CvssData {
    #[serde(rename = "attackVector")]
    attack_vector: Option<String>,
    #[serde(rename = "attackComplexity")]
    attack_complexity: Option<String>,
    #[serde(rename = "privilegesRequired")]
    privileges_required: Option<String>,
    #[serde(rename = "userInteraction")]
    user_interaction: Option<String>,
    #[serde(rename = "confidentialityImpact")]
    confidentiality_impact: Option<String>,
    #[serde(rename = "integrityImpact")]
    integrity_impact: Option<String>,
    #[serde(rename = "availabilityImpact")]
    availability_impact: Option<String>,
}

#[derive(Deserialize, Debug)]
struct CvssMetricItem {
    #[serde(rename = "cvssData")]
    cvss_data: CvssData,
}

#[derive(Deserialize, Debug)]
struct MetricsNode {
    #[serde(rename = "cvssMetricV31")]
    cvss_metric_v31: Option<Vec<CvssMetricItem>>,
    #[serde(rename = "cvssMetricV40")]
    cvss_metric_v40: Option<Vec<CvssMetricItem>>,
}

#[derive(Deserialize, Debug)]
struct CveNode {
    id: String,
    metrics: Option<MetricsNode>,
}

#[derive(Deserialize, Debug)]
struct NvdItem {
    id: Option<String>,
    cve: Option<CveNode>,
    metrics: Option<MetricsNode>,
}

// ---------------------------------------------------------------------------
// CVSS Metrics to numeric value mappings (0.0 to 10.0)
// ---------------------------------------------------------------------------

fn map_av(val: Option<&str>) -> f64 {
    match val {
        Some("NETWORK") => 10.0,
        Some("ADJACENT_NETWORK") => 7.5,
        Some("LOCAL") => 5.0,
        Some("PHYSICAL") => 2.5,
        _ => 0.0,
    }
}

fn map_ac(val: Option<&str>) -> f64 {
    match val {
        Some("LOW") => 10.0,
        Some("HIGH") => 4.0,
        _ => 0.0,
    }
}

fn map_pr(val: Option<&str>) -> f64 {
    match val {
        Some("NONE") => 10.0,
        Some("LOW") => 5.0,
        Some("HIGH") => 2.5,
        _ => 0.0,
    }
}

fn map_ui(val: Option<&str>) -> f64 {
    match val {
        Some("NONE") => 10.0,
        Some("REQUIRED") | Some("PASSIVE") => 4.0,
        Some("ACTIVE") => 8.0,
        _ => 0.0,
    }
}

fn map_impact(val: Option<&str>) -> f64 {
    match val {
        Some("HIGH") => 10.0,
        Some("LOW") => 5.0,
        Some("NONE") => 0.0,
        _ => 0.0,
    }
}

// ---------------------------------------------------------------------------
// Image Rendering and Vector Operations
// ---------------------------------------------------------------------------

const CATEGORIES: [&str; 7] = [
    "Attack Vector\n(AV)",
    "Complexity\n(AC)",
    "Privileges\n(PR)",
    "User Interaction\n(UI)",
    "Confidentiality\n(C)",
    "Integrity\n(I)",
    "Availability\n(A)",
];

fn extract_cve_and_values(json_str: &str) -> Result<(String, Vec<f64>), String> {
    let item: NvdItem = serde_json::from_str(json_str).map_err(|e| e.to_string())?;

    let (cve_id, metrics) = if let Some(cve) = item.cve {
        (cve.id, cve.metrics)
    } else {
        (
            item.id.unwrap_or_else(|| "CVE-UNKNOWN".to_string()),
            item.metrics,
        )
    };

    let metrics = metrics.ok_or_else(|| format!("Metrics not found for {}", cve_id))?;

    let cvss_data = if let Some(ref v31) = metrics.cvss_metric_v31 {
        v31.first().map(|m| &m.cvss_data)
    } else if let Some(ref v40) = metrics.cvss_metric_v40 {
        v40.first().map(|m| &m.cvss_data)
    } else {
        None
    }
    .ok_or_else(|| format!("CVSS metrics not found in record {}", cve_id))?;

    let values = vec![
        map_av(cvss_data.attack_vector.as_deref()),
        map_ac(cvss_data.attack_complexity.as_deref()),
        map_pr(cvss_data.privileges_required.as_deref()),
        map_ui(cvss_data.user_interaction.as_deref()),
        map_impact(cvss_data.confidentiality_impact.as_deref()),
        map_impact(cvss_data.integrity_impact.as_deref()),
        map_impact(cvss_data.availability_impact.as_deref()),
    ];

    Ok((cve_id, values))
}

fn render_svg(cve_id: &str, values: &[f64], width: u32, height: u32) -> Result<String, String> {
    let mut svg_buffer = String::new();
    {
        let root = SVGBackend::with_string(&mut svg_buffer, (width, height)).into_drawing_area();
        root.fill(&WHITE).map_err(|e| e.to_string())?;

        let center = ((width / 2) as i32, (height / 2) as i32);
        let radius = (width.min(height) as f64) * 0.35;
        let num_vars = CATEGORIES.len();
        let angle_step = 2.0 * PI / (num_vars as f64);

        // Concentric circular grid lines
        for i in 1..=5 {
            let r = radius * (i as f64 / 5.0);
            root.draw(&Circle::new(center, r as i32, &RGBColor(200, 200, 200)))
                .map_err(|e| e.to_string())?;
        }

        let mut polygon_points = Vec::with_capacity(num_vars);

        for (idx, &val) in values.iter().enumerate() {
            let angle = (idx as f64 * angle_step) - (PI / 2.0);
            let cos_a = angle.cos();
            let sin_a = angle.sin();

            let axis_x = center.0 + (radius * cos_a) as i32;
            let axis_y = center.1 + (radius * sin_a) as i32;
            root.draw(&PathElement::new(
                vec![center, (axis_x, axis_y)],
                &RGBColor(220, 220, 220),
            ))
            .map_err(|e| e.to_string())?;

            let normalized = (val / 10.0).clamp(0.0, 1.0);
            let pt_r = radius * normalized;
            let pt_x = center.0 + (pt_r * cos_a) as i32;
            let pt_y = center.1 + (pt_r * sin_a) as i32;
            polygon_points.push((pt_x, pt_y));

            let label_x = center.0 + ((radius + 25.0) * cos_a) as i32;
            let label_y = center.1 + ((radius + 25.0) * sin_a) as i32;

            for (line_idx, line) in CATEGORIES[idx].lines().enumerate() {
                root.draw(&Text::new(
                    line.to_string(),
                    (label_x - 18, label_y - 10 + (line_idx as i32 * 12)),
                    ("sans-serif", 10).into_font(),
                ))
                .map_err(|e| e.to_string())?;
            }
        }

        if !polygon_points.is_empty() {
            let mut closed_polygon = polygon_points.clone();
            closed_polygon.push(polygon_points[0]);

            root.draw(&Polygon::new(
                polygon_points,
                RGBColor(217, 83, 79).mix(0.3),
            ))
            .map_err(|e| e.to_string())?;

            root.draw(&PathElement::new(
                closed_polygon,
                ShapeStyle::from(&RGBColor(217, 83, 79)).stroke_width(2),
            ))
            .map_err(|e| e.to_string())?;
        }

        root.draw(&Text::new(
            format!("CVSS Metrics — {}", cve_id),
            (20, 20),
            ("sans-serif", 14).into_font().style(FontStyle::Bold),
        ))
        .map_err(|e| e.to_string())?;

        root.present().map_err(|e| e.to_string())?;
    }

    Ok(svg_buffer)
}

fn render_svg_to_png(svg_str: &str, width: u32, height: u32) -> Result<Vec<u8>, String> {
    let opt = usvg::Options::default();
    let tree = usvg::Tree::from_str(svg_str, &opt).map_err(|e| e.to_string())?;

    let mut pixmap = tiny_skia::Pixmap::new(width, height)
        .ok_or_else(|| "Failed to allocate memory for PNG".to_string())?;

    resvg::Tree::from_usvg(&tree).render(
        usvg::Transform::default(),
        &mut pixmap.as_mut(),
    );

    pixmap.encode_png().map_err(|e| e.to_string())
}

fn process_single_json(json_str: &str, width: u32, height: u32) -> Result<(String, Vec<u8>), String> {
    let (cve_id, values) = extract_cve_and_values(json_str)?;
    let svg = render_svg(&cve_id, &values, width, height)?;
    let png_bytes = render_svg_to_png(&svg, width, height)?;
    Ok((cve_id, png_bytes))
}

// ---------------------------------------------------------------------------
// PyO3 Class Binding
// ---------------------------------------------------------------------------

#[pyclass]
pub struct CVSSRadarChartGenerator {
    width: u32,
    height: u32,
}

#[pymethods]
impl CVSSRadarChartGenerator {
    #[new]
    #[pyo3(signature = (width=600, height=600))]
    pub fn new(width: u32, height: u32) -> Self {
        Self { width, height }
    }

    pub fn generate_chart<'py>(
        &self,
        py: Python<'py>,
        json_data: String,
    ) -> PyResult<Bound<'py, PyAny>> {
        let width = self.width;
        let height = self.height;

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let res = task::spawn_blocking(move || {
                process_single_json(&json_data, width, height)
            })
            .await
            .map_err(|e| PyValueError::new_err(e.to_string()))?
            .map_err(|e| PyValueError::new_err(e))?;

            Ok(res)
        })
    }

    pub fn generate_batch<'py>(
        &self,
        py: Python<'py>,
        json_list: Vec<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let width = self.width;
        let height = self.height;
        let json_list = Arc::new(json_list);

        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let mut tasks = Vec::with_capacity(json_list.len());

            for item in json_list.iter() {
                let json_str = item.clone();
                tasks.push(task::spawn_blocking(move || {
                    process_single_json(&json_str, width, height)
                }));
            }

            let mut results = Vec::with_capacity(tasks.len());
            for task in tasks {
                match task.await {
                    Ok(Ok(data)) => results.push(data),
                    Ok(Err(e)) => eprintln!("Error generating item: {}", e),
                    Err(e) => eprintln!("Task execution error: {}", e),
                }
            }

            Ok(results)
        })
    }
}

#[pymodule]
fn chart_lib(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CVSSRadarChartGenerator>()?;
    Ok(())
}