import maltese.mc.Btor2

object BtorViewer extends App {
  require(args.length == 1, "Please supply a filename")
  val path = os.Path(args.last, os.pwd)
  val sys = Btor2.load(path)
  println(sys.serialize)
}
