module Counter(
  input        clock,
  input        reset,
  input        io_enable,
  output [3:0] io_count,
  output       io_overflow
);
  reg [3:0] count; // @[Counter.scala 17:22]
  reg  overflow; // @[Counter.scala 18:25]
  wire [3:0] _count_T_1 = count + 4'h1; // @[Counter.scala 20:20]
  wire  _GEN_1 = count == 4'h7 | overflow; // @[Counter.scala 22:29 23:14 18:25]
  assign io_count = count; // @[Counter.scala 26:12]
  assign io_overflow = overflow; // @[Counter.scala 27:15]
  always @(posedge clock) begin
    if (reset) begin // @[Counter.scala 17:22]
      count <= 4'h0; // @[Counter.scala 17:22]
    end else if (io_enable) begin // @[Counter.scala 19:19]
      count <= _count_T_1; // @[Counter.scala 20:11]
    end
    if (reset) begin // @[Counter.scala 18:25]
      overflow <= 1'h0; // @[Counter.scala 18:25]
    end else begin
      overflow <= _GEN_1;
    end
  end
endmodule
