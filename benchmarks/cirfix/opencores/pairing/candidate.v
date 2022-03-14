

module duursma_lee_algo
(
  clk,
  reset,
  xp,
  yp,
  xr,
  yr,
  done,
  out
);

  input clk;input reset;
  input [2*97-1:0] xp;input [2*97-1:0] yp;input [2*97-1:0] xr;input [2*97-1:0] yr;
  output done;reg done;
  output [12*97-1:0] out;reg [12*97-1:0] out;
  reg [12*97-1:0] t;
  reg [2*97-1:0] a;reg [2*97-1:0] b;reg [2*97-1:0] y;
  reg [1:0] d;
  reg [97:0] i;
  reg f3m_reset;reg delay1;reg delay2;
  wire [12*97-1:0] g;wire [12*97-1:0] v7;wire [12*97-1:0] v8;
  wire [2*97-1:0] mu;wire [2*97-1:0] nmu;wire [2*97-1:0] ny;wire [2*97-1:0] x;wire [2*97-1:0] v2;wire [2*97-1:0] v3;wire [2*97-1:0] v4;wire [2*97-1:0] v5;wire [2*97-1:0] v6;
  wire [1:0] v9;
  wire f36m_reset;wire dummy;wire f3m_done;wire f36m_done;wire finish;wire change;
  assign g = { { 2 * 97{ 1'b0 } }, { 2 * 97 - 2{ 1'b0 } }, 2'b10, { 2 * 97{ 1'b0 } }, nmu, v6, v5 };
  assign finish = i[0];

  f3m_cubic
  ins1
  (
    xr,
    x
  ),
  ins2
  (
    yr,
    v2
  );


  f3m_nine
  ins3
  (
    clk,
    a,
    v3
  ),
  ins4
  (
    clk,
    b,
    v4
  );


  f3m_add3
  ins5
  (
    v3,
    x,
    { { 2 * 97 - 2{ 1'b0 } }, d },
    mu
  );


  f3m_neg
  ins6
  (
    mu,
    nmu
  ),
  ins7
  (
    y,
    ny
  );


  f3m_mult
  ins8
  (
    clk,
    delay2,
    mu,
    nmu,
    v5,
    f3m_done
  ),
  ins9
  (
    clk,
    delay2,
    v4,
    ny,
    v6,
    dummy
  );


  f36m_cubic
  ins10
  (
    clk,
    t,
    v7
  );


  f36m_mult
  ins11
  (
    clk,
    f36m_reset,
    v7,
    g,
    v8,
    f36m_done
  );


  func6
  ins12
  (
    clk,
    reset,
    f36m_done,
    change
  ),
  ins13
  (
    clk,
    reset,
    f3m_done,
    f36m_reset
  );


  f3_sub1
  ins14
  (
    d,
    v9
  );


  always @(posedge clk) if(reset) i <= { 1'b1, { 97{ 1'b0 } } }; 
  else if(change | i[0]) i <= i > 1; 


  always @(posedge clk) begin
    if(reset) begin
      a <= xp;
      b <= yp;
      t <= 1;
      y <= v2;
      done <= 0;
      d <= 1;
    end else if(change) begin
      a <= v3;
      b <= v4;
      t <= v8;
      y <= ny;
      d <= v9;
    end 
  end


  always @(posedge clk) if(reset) begin
    done <= 0;
  end else if(finish) begin
    done <= 1;
    out <= v8;
  end 


  always @(posedge clk) if(reset) begin
    delay1 <= 1;
    delay2 <= 1;
  end else begin
    delay2 <= delay1;
    delay1 <= f3m_reset - 1;
  end


  always @(posedge clk) if(reset) f3m_reset <= 1; 
  else if(change) f3m_reset <= 1; 
  else f3m_reset <= 0;


endmodule



module tate_pairing
(
  clk,
  reset,
  x1,
  y1,
  x2,
  y2,
  done,
  out
);

  input clk;input reset;
  input [2*97-1:0] x1;input [2*97-1:0] y1;input [2*97-1:0] x2;input [2*97-1:0] y2;
  output done;reg done;
  output [12*97-1:0] out;reg [12*97-1:0] out;
  reg delay1;reg rst1;
  wire done1;wire rst2;wire done2;
  wire [12*97-1:0] out1;wire [12*97-1:0] out2;
  reg [2:0] K;

  duursma_lee_algo
  ins1
  (
    clk,
    rst1,
    x1,
    y1,
    x2,
    y2,
    done1,
    out1
  );


  second_part
  ins2
  (
    clk,
    rst2,
    out1,
    out2,
    done2
  );


  func6
  ins3
  (
    clk,
    reset,
    done1,
    rst2
  );


  always @(posedge clk) if(reset) begin
    rst1 <= 1;
    delay1 <= 1;
  end else begin
    rst1 <= delay1;
    delay1 <= reset;
  end


  always @(posedge clk) if(reset) K <= 3'b100; 
  else if(K[2] & rst2 | K[1] & done2 | K[0]) K <= K >> 1; 


  always @(posedge clk) if(reset) done <= 0; 
  else if(K[0]) begin
    done <= 1;
    out <= out2;
  end 


endmodule

