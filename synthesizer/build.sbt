val commonSettings = Seq(
  version := "0.1",
  organization := "edu.berkeley.cs",
  Compile / scalaSource := baseDirectory.value / "src",
  Compile / resourceDirectory := baseDirectory.value / "src" / "resources",
  Test / scalaSource := baseDirectory.value / "test",
  Test / resourceDirectory := baseDirectory.value / "test" / "resources",
  scalaVersion := "2.13.10",
  scalacOptions := Seq("-deprecation", "-unchecked", "-language:reflectiveCalls", "-Xcheckinit"),
)


lazy val main = (project in file("."))
  .settings(name := "bug-fix-synthesizer")
  .settings(commonSettings)
  .settings(
    // BDD library
    libraryDependencies += "com.github.com-github-javabdd" % "com.github.javabdd" % "2.0.0",
    // command line argument parser
    libraryDependencies += "com.github.scopt" %% "scopt" % "4.0.1",
    // lib os for file system access
    libraryDependencies += "com.lihaoyi" %% "os-lib" % "0.8.0",
  )
  .settings(
    libraryDependencies += "org.scalatest" %% "scalatest" % "3.2.10" % Test,
  )

